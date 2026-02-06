---
name: dialogue-phase-rules
description: >
  Enforce phased collaboration: Phase 1 design only (no implementation), Phase 2 module-by-module code, Phase 3 integration.
  Use when users want strict conversation guardrails, staged delivery, or constraints (e.g., no third-party libs, no malloc, must be C++17).
---

# Dialogue Phase Rules

## When to use
- User asks for process/guardrails before coding, phased delivery, or design-first workflow.
- Requests to delay implementation until design is approved.
- Tasks with strict constraints (language standard, banned libraries, memory rules).

## Workflow
1. **Declare phases upfront**  
   - Phase 1: design only; no implementation code.  
   - Phase 2: implement each module separately.  
   - Phase 3: integrate modules, run tests, final polish.
2. **Restate constraints** given by user (e.g., “no third-party libraries”, “no malloc”, “C++17 only”). Ask for missing ones if unclear.
3. **Phase 1 deliverables (required)**: module diagram/outline, interface table (inputs/outputs/types), data flow, error handling plan, test plan (unit/edge/integration). No code.
4. **Gate**: Ask for approval to proceed to Phase 2.
5. **Phase 2**: implement module-by-module following the approved design; keep modules isolated; note any deviations needed for constraints.
6. **Phase 3**: integrate modules, handle wiring, run/describe tests, and present final result with known gaps.

## Ready-to-use prompt
Copy/paste to start a session with another AI:  
“先输出设计方案和模块划分，不要写任何实现代码。等我确认后，再按模块逐个实现。阶段输出：Phase 1 只输出设计；Phase 2 写模块代码；Phase 3 集成。每阶段要给：模块图/接口表/数据流/错误处理/测试计划。必须满足：不允许引第三方库；不能 malloc；必须 C++17。”

## Handling variations
- **User insists on direct code**: restate guardrails and ask for confirmation to skip phases; proceed only if explicitly approved.
- **New constraints midstream**: update the constraint list, restate impacts, and reconfirm before continuing.
- **Conflicting constraints**: highlight the conflict, propose a resolution, and wait for approval.

## Outputs to provide
- At each phase, clearly label the phase and deliverables.  
- Keep responses concise; avoid code in Phase 1; avoid integration in Phase 2.
