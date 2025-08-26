import re
import sys
import yaml
import argparse
from typing import Any, List, Dict, Tuple

# ==============================================================================
# 1. 파서(Parser) 로직: (변경 없음)
# ==============================================================================
def find_yaml_block(content: str) -> str:
    fenced_match = re.search(r"```yaml\s*\n(.*?)\n```", content, re.DOTALL)
    if fenced_match:
        return fenced_match.group(1)
    frontmatter_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL | re.MULTILINE)
    if frontmatter_match:
        return frontmatter_match.group(1)
    raise ValueError("YAML 블록을 찾을 수 없습니다. ```yaml ... ``` 또는 --- ... --- 형식을 사용하세요.")

def load_mdc_file(filepath: str) -> Dict[str, Any]:
    print(f"파일 로드 중: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        yaml_part = find_yaml_block(content)
        data = yaml.safe_load(yaml_part)
        if not isinstance(data, dict):
            raise yaml.YAMLError("YAML 내용이 올바른 딕셔너리(객체) 형식이 아닙니다.")
        return data
    except Exception as e:
        print(f"오류: {filepath} 파일을 처리하는 중 문제가 발생했습니다.", file=sys.stderr)
        print(f"  - {e}", file=sys.stderr)
        raise

# ==============================================================================
# 2. 검증 엔진(Validation Engine) 로직: (대대적인 리팩토링)
# ==============================================================================
class ValidationError:
    """검증 오류 정보를 체계적으로 담기 위한 클래스."""
    def __init__(self, message: str, path: str = "N/A", rule_id: str = "N/A"):
        self.message = message
        self.path = path
        self.rule_id = rule_id

    def __str__(self) -> str:
        return f"[{self.rule_id}] 경로 '{self.path}': {self.message}"

class Z0Validator:
    """Z0-Core 헌법에 따라 MDC 문서의 유효성을 검사하는 검증기 클래스."""
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema

    def _get_value_at_path(self, document: Dict[str, Any], path: str) -> Tuple[bool, Any]:
        """점(.)으로 구분된 경로를 따라 문서에서 값을 찾아 반환합니다. (중복 로직 제거)"""
        keys = path.split('.')
        current_level = document
        for key in keys:
            if isinstance(current_level, dict) and key in current_level:
                current_level = current_level[key]
            else:
                return (False, None)
        return (True, current_level)

    def validate(self, document: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        """주어진 문서를 검증하고, (유효성 여부, 오류 객체 목록)을 반환합니다."""
        errors: List[ValidationError] = []
        if document.get("validationMode") == "strict":
            self._validate_strict_required_sections(document, errors)
            self._validate_require_fields(document, errors)
            self._validate_require_if(document, errors)
        return not errors, errors

    def _validate_strict_required_sections(self, document: Dict[str, Any], errors: List[ValidationError]):
        strict_profile = self.schema.get("validationProfiles", {}).get("strict", {})
        required_paths = strict_profile.get("required", [])
        for path in required_paths:
            found, _ = self._get_value_at_path(document, path)
            if not found:
                errors.append(ValidationError(f"필수 필드가 누락되었습니다.", path=path, rule_id="strict.required"))

    def _validate_require_fields(self, document: Dict[str, Any], errors: List[ValidationError]):
        strict_profile = self.schema.get("validationProfiles", {}).get("strict", {})
        rules = strict_profile.get("requireFields", {})
        for path_pattern, required_keys in rules.items():
            path_base = path_pattern.replace("[*]", "")
            found, list_items = self._get_value_at_path(document, path_base)
            if found and isinstance(list_items, list):
                for index, item in enumerate(list_items):
                    current_path = f"{path_base}[{index}]"
                    if isinstance(item, dict):
                        for r_key in required_keys:
                            if r_key not in item:
                                errors.append(ValidationError(f"항목에 필수 키 '{r_key}'가 없습니다.", path=current_path, rule_id="strict.requireFields"))
                    else:
                        errors.append(ValidationError("항목이 딕셔너리(객체)가 아닙니다.", path=current_path, rule_id="strict.requireFields"))

    def _validate_require_if(self, document: Dict[str, Any], errors: List[ValidationError]):
        strict_profile = self.schema.get("validationProfiles", {}).get("strict", {})
        conditional_rules = strict_profile.get("requireIf", [])
        for rule in conditional_rules:
            condition_path_full, expected_value_str = [x.strip() for x in rule.get("when", "").split('==')]
            condition_path = condition_path_full.replace('$.', '')
            expected_value = expected_value_str.strip("'\"")
            
            found, actual_value = self._get_value_at_path(document, condition_path)
            if found and str(actual_value) == expected_value:
                for path_to_check in rule.get("paths", []):
                    if not self._path_exists(document, path_to_check): # Helper to check existence
                        errors.append(ValidationError(f"필드가 반드시 필요합니다 (조건 '{rule['when']}' 충족됨).", path=path_to_check, rule_id="strict.requireIf"))

    def _path_exists(self, document: Dict[str, Any], path: str) -> bool:
        """_get_value_at_path의 간단한 존재 여부 확인 버전."""
        exists, _ = self._get_value_at_path(document, path)
        return exists

# ==============================================================================
# 3. 실행(Main) 로직: (argparse 적용으로 강화)
# ==============================================================================
def main():
    """메인 검증 로직을 실행합니다."""
    parser = argparse.ArgumentParser(description="Z0-Core 헌법에 따라 .MDC 파일의 유효성을 검증합니다.")
    parser.add_argument("target_file", help="검증할 대상 .MDC 파일 경로")
    parser.add_argument("schema_file", help="기준이 될 Z0-Core 헌법 파일 경로")
    args = parser.parse_args()

    try:
        print("="*50)
        print("MDC 검증기 실행")
        print("="*50)
        
        z0_core_rules = load_mdc_file(args.schema_file)
        print("✅ 헌법 파일 로드 완료.")

        document_to_check = load_mdc_file(args.target_file)
        print("✅ 검증 대상 파일 로드 완료.")
        
        validator = Z0Validator(z0_core_rules)
        is_valid, errors = validator.validate(document_to_check)
        
        print("-" * 50)
        if is_valid:
            print("🎉 [결과] 합격: 모든 규칙을 준수합니다.")
            sys.exit(0)
        else:
            print(f"🚨 [결과] 불합격: {len(errors)}개의 오류가 발견되었습니다.")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)

    except Exception:
        print("\n🚨 심각한 오류로 인해 검증을 중단합니다.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()