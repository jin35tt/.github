import unittest
import yaml
from mdc_validator import load_mdc_file, Z0Validator, ValidationError

class TestMdcValidator(unittest.TestCase):

    def setUp(self):
        """테스트 시작 전, 헌법 파일을 미리 로드합니다."""
        self.z0_core_rules = load_mdc_file("Z0-Core-Universal-MDC-Architecture.md")

    def test_strict_mode_with_missing_section(self):
        """
        [TEST] strict 모드에서 필수 섹션('domain')이 누락된 경우, 검증은 실패해야 한다.
        """
        print("\n--- [TEST] strict 모드 필수 섹션 누락 검사 실행 ---")
        
        invalid_mdc_content = """
        moduleContract:
          moduleName: "TEST"
        feature:
          featureName: "InvalidFeature"
          description: "A feature for testing"
        compatibility:
          version: "TEST.v1.0.0"
        validationMode: "strict"
        # 'domain' 섹션이 의도적으로 누락됨
        interfaces: { inputs: [], outputs: [] }
        pipeline: []
        dataSchemas: []
        performance: { metricsTable: [] }
        tests: []
        extensions: {}
        """
        invalid_document = yaml.safe_load(invalid_mdc_content)

        validator = Z0Validator(self.z0_core_rules)
        is_valid, errors = validator.validate(invalid_document)

        self.assertFalse(is_valid, "검증 결과가 '유효하지 않음(False)'이어야 합니다.")
        # 이제 errors[0]는 객체이므로, str()로 변환하여 문자열로 만든 뒤 내용을 검사합니다.
        self.assertIn("'domain.entities'", str(errors[0]), "오류 메시지에 'domain.entities'가 포함되어야 합니다.")
        
        print("--- [TEST] 예상대로 'domain.entities' 누락 오류를 발견함 (성공) ---")

    def test_strict_mode_with_missing_require_fields(self):
        """
        [TEST] strict 모드에서 requireFields 규칙을 위반한 경우 (budget_ms 누락), 검증은 실패해야 한다.
        """
        print("\n--- [TEST] requireFields 규칙 위반 검사 실행 ---")
        
        invalid_mdc_content = """
        moduleContract: { moduleName: "TEST" }
        feature: { featureName: "TestFeature", description: "A feature for testing" }
        compatibility: { version: "TEST.v1.0.0" }
        validationMode: "strict"
        domain: { entities: [], rules: [] }
        interfaces: { inputs: [], outputs: [] }
        pipeline: []
        dataSchemas: []
        performance:
          metricsTable:
            - metric: "SomeMetric.DurationMs"
              timeout_s: 5
        tests: []
        extensions: {}
        """
        invalid_document = yaml.safe_load(invalid_mdc_content)

        validator = Z0Validator(self.z0_core_rules)
        is_valid, errors = validator.validate(invalid_document)

        self.assertFalse(is_valid)
        self.assertIn("'budget_ms'", str(errors[0]))
        
        print("--- [TEST] 예상대로 'budget_ms' 누락 오류를 발견함 (성공) ---")

    def test_strict_mode_with_missing_require_if_fields(self):
        """
        [TEST] docType이 'mdc-constitution'일 때 requireIf 규칙을 위반한 경우, 검증은 실패해야 한다.
        """
        print("\n--- [TEST] requireIf 규칙 위반 검사 실행 ---")
        
        invalid_constitution_mdc = """
        mgiContract:
          docType: "mdc-constitution"
          comms: { mode: "EventBus" }
        validationMode: "strict"
        moduleContract: { moduleName: "CORE" }
        feature: { featureName: "CoreSchema", description: "The constitution itself" }
        compatibility: { version: "CORE.v1.0.0" }
        domain: { entities: [], rules: [] }
        interfaces: { inputs: [], outputs: [] }
        pipeline: []
        dataSchemas: []
        performance: { metricsTable: [] }
        tests: []
        extensions: {}
        """
        invalid_document = yaml.safe_load(invalid_constitution_mdc)

        validator = Z0Validator(self.z0_core_rules)
        is_valid, errors = validator.validate(invalid_document)

        self.assertFalse(is_valid)
        self.assertIn("'mergePolicy.arrayKeyBy'", str(errors[0]))
        
        print("--- [TEST] 예상대로 'mergePolicy.arrayKeyBy' 누락 오류를 발견함 (성공) ---")

if __name__ == '__main__':
    unittest.main()