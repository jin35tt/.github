[META INSTRUCTION BLOCK - FOR AI ONLY]
이 부록은 위 `Z0-Core` 헌법을 사용하여 실제 기능(`UserAuthentication`)을 어떻게 설계하는지 보여주는 **검증 가능한(Verifiable) 참조 구현**이다. 이 예시는 `validationMode: "strict"`의 모든 요구사항을 충족하며, 보강된 모든 스키마 규칙을 통과한다..


```yaml
# ── 1. Common ───────────────────────────────────────────────
moduleContract:
  moduleName: "AUTH"
feature:
  featureName: "UserAuthentication"
  description: "사용자 이메일과 비밀번호를 이용한 로그인 처리 및 세션 관리"
compatibility:
  version: "AUTH.v1.0.0"
capabilities:
  usesNetworking: true
  usesHierarchicalTags: true
validationMode: "strict"

# ── 2. Domain ───────────────────────────────────────────────
domain:
  entities:
    - name: UserSession
      properties:
        - { name: UserID, type: string, tag: "Auth.Session.UserID" }
        - { name: AuthToken, type: string, tag: "Auth.Session.Token" }
        - { name: Status, type: enum, values: ["LoggedIn", "LoggedOut", "Expired"] }
  rules:
    - id: "RULE-AUTH-01"
      description: "인증 토큰(AuthToken)은 발급 후 60분 뒤 만료된다."

# ── 3. Architecture ───────────────────────────────────────────
interfaces:
  inputs:
    - kind: "DirectAPI"
      name: "AuthService::RequestLogin"
      params: ["Email", "Password"]
  outputs:
    - kind: "EventBus"
      name: "AuthEvents::OnLoginStatusChanged"
      payload:
        struct: "LoginStatusPayload"
        fields: ["UserID", "NewStatus", "AuthToken"]
pipeline:
  - step: ValidateInput
    where: "MainThread"
    authority: "ClientOnly"
    effects:
      - "guard: if email or password format is invalid, throw ValidationException"
  - step: AuthenticateWithService
    where: "BackgroundWorker"
    authority: "ClientOnly"
    effects:
      - "async: POST /api/auth/login with {Email, Password}"
      - "returns: {UserID, AuthToken}"
  - step: UpdateLocalSession
    where: "MainThread"
    authority: "ClientOnly"
    effects:
      - "mutate: UserSession.Status = 'LoggedIn'"
      - "mutate: LocalStorage.AuthToken = AuthToken"
      - "emit: AuthEvents::OnLoginStatusChanged"
dataSchemas:
  - id: "LoginStatusPayload"
    type: "struct"
    fields:
      - { name: "UserID", type: "string" }
      - { name: "NewStatus", type: "string" }
      - { name: "AuthToken", type: "string" }

# ── 4. Quality ────────────────────────────────────────────────
performance:
  metricsTable:
    - metric: "AuthenticateWithService.DurationMs"
      budget_ms: 500
      timeout_s: 10
tests:
  - id: "IT-AUTH-LOGIN-01"
    type: "integration"
    scenario: "유효한 자격증명으로 로그인 시 세션이 활성화되고 이벤트가 발생한다."
    given: "User is LoggedOut"
    when: "AuthService::RequestLogin with valid credentials"
    then:
      - "UserSession.Status is 'LoggedIn'"
      - "AuthEvents::OnLoginStatusChanged is emitted with status 'LoggedIn'"

# ── 5. Extensions ──────────────────────────────────────────────
extensions: {}
```
