export const MODULES = [
  {
    id: 7,
    name: '旗舰实战：智能客服工单分派',
    description: '先把一个真实业务决策做深：需求建模、异常保护、私有场景判题、代码答辩与故障修复。',
    taskCount: 1,
    tasks: [
      {
        id: '7-1',
        title: '为客服 Agent 实现可上线的工单分派引擎',
        starter: `def dispatch_ticket(ticket, agents, now_minutes):
    """根据业务规则返回稳定、可审计的工单分派结果。"""
    raise NotImplementedError("请实现工单分派规则")`,
      },
    ],
  },
]

export const MOCK_PROGRESS = { 7: 0 }
