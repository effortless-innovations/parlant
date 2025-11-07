# travel_voice_agent.py

from dotenv import load_dotenv
import parlant.sdk as p
import asyncio
from datetime import datetime


# 获取可用的目的地
@p.tool
async def get_available_destinations(context: p.ToolContext) -> p.ToolResult:
    return p.ToolResult(
        [
            "北京",
            "上海",
            "广州",
            "成都",
        ]
    )


# 获取可用的航班
@p.tool
async def get_available_flights(context: p.ToolContext, destination: str) -> p.ToolResult:
    # 模拟从预订系统中获取可用航班
    return p.ToolResult(
        data=[
            "航班 CA123 - 6月15日 09:00, ¥5800",
            "航班 MU321 - 6月16日 14:30, ¥5200",
            "航班 CZ987 - 6月17日 18:45, ¥4800",
        ]
    )


# 获取备选航班
@p.tool
async def get_alternative_flights(context: p.ToolContext, destination: str) -> p.ToolResult:
    # 模拟不同日期备选航班
    return p.ToolResult(
        data=[
            "航班 CA485 - 6月25日 11:00, ¥6200",
            "航班 MU516 - 7月2日 16:15, ¥5500",
        ]
    )


# 预订航班
@p.tool
async def book_flight(context: p.ToolContext, flight_details: str) -> p.ToolResult:
    # 模拟预订航班，使用客户名称从上下文中获取客户名称
    return p.ToolResult(
        data=f"航班已预订：{flight_details}，乘客：{p.Customer.current.name}。"
        f"确认号：TRV-{datetime.now().strftime('%Y%m%d')}-001"
    )


# 查询预订状态
@p.tool
async def get_booking_status(context: p.ToolContext, confirmation_number: str) -> p.ToolResult:
    # 模拟从预订系统中获取预订信息，使用客户ID从上下文中获取预订信息
    booking_info = {
        "status": "已确认",
        "details": "6月15日 09:00 飞往北京的航班。座位号：12A。",
        "notes": "请在航班起飞前24小时开始办理值机手续。",
    }

    return p.ToolResult(
        data={
            "status": booking_info["status"],
            "details": booking_info["details"],
            "notes": booking_info["notes"],
        }
    )


async def add_domain_glossary(agent: p.Agent) -> None:
    await agent.create_term(
        name="Office Phone Number",
        description="我们旅行社办公室的电话号码：400-888-8888",
        synonyms=["contact number", "customer service number", "support line"],
    )

    await agent.create_term(
        name="Baggage Policy",
        description="This describes the rules and fees associated with checked and carry-on baggage.",
        synonyms=["luggage policy", "baggage rules", "carry-on policy"],
    )

    await agent.create_term(
        name="Cancellation Policy",
        description="This outlines the terms and conditions for cancelling a booking, including any fees or deadlines.",
        synonyms=["refund policy", "cancellation terms"],
    )

    await agent.create_term(
        name="Travel Insurance",
        description="An optional service that provides coverage for trip cancellations, medical emergencies, lost luggage, and other travel-related issues.",
        synonyms=["insurance", "trip protection", "travel protection"],
    )

    # Add other specific terms and definitions here, as needed...


async def create_flight_booking_journey(server: p.Server, agent: p.Agent) -> p.Journey:
    # 创建预订航班的旅程
    journey = await agent.create_journey(
        title="预订航班",
        description="Helps the customer find and book a flight to their desired destination.",
        conditions=["客户想要预订航班"],
    )

    # 首先，询问目的地
    t0 = await journey.initial_state.transition_to(chat_state="询问目的地")

    # 然后，询问首选出行日期
    t1 = await t0.target.transition_to(chat_state="询问首选出行日期")

    # 加载可用航班到上下文中
    t2 = await t1.target.transition_to(tool_state=get_available_flights)

    # 展示可用航班
    # 我们会根据客户的选择进行条件跳转
    t3 = await t2.target.transition_to(
        chat_state="展示可用航班并询问哪个适合他们"
    )

    # 我们会从客户选择航班的顺利路径开始
    t4 = await t3.target.transition_to(
        chat_state="收集乘客信息并在继续前确认预订详情",
        condition="客户选择了航班",
    )

    t5 = await t4.target.transition_to(
        tool_state=book_flight,
        condition="客户确认了预订详情",
    )
    t6 = await t5.target.transition_to(chat_state="提供确认号和预订摘要")
    await t6.target.transition_to(state=p.END_JOURNEY)

    # 否则，如果所有航班都不适合，提供备选日期
    t7 = await t3.target.transition_to(
        tool_state=get_alternative_flights,
        condition="这些航班都不适合客户",
    )
    t8 = await t7.target.transition_to(chat_state="展示备选航班并询问是否有合适的")

    # 如果客户选择了航班，返回顺利路径
    await t8.target.transition_to(state=t4.target, condition="客户选择了航班")

    # Otherwise, ask them to call the office or check our website
    # 否则，建议客户致电我们的办公室或访问我们的网站以获取更多选项
    t9 = await t8.target.transition_to(
        chat_state="建议致电我们的办公室或访问我们的网站以获取更多选项",
        condition="备选航班也都不适合",
    )
    await t9.target.transition_to(state=p.END_JOURNEY)

    # 处理边缘情况故意使用指南
    # 例如，客户提到需要紧急出行或这是紧急情况
    await journey.create_guideline(
        condition="客户提到需要紧急出行或这是紧急情况",
        action="引导他们立即致电我们的办公室以获得优先预订协助",
    )

    await journey.create_guideline(
        condition="客户询问签证要求",
        action="告知他们签证要求因目的地和国籍而异，建议他们咨询大使馆或领事馆",
    )

    return journey


async def create_booking_status_journey(server: p.Server, agent: p.Agent) -> p.Journey:
    # 创建查询预订状态的旅程
    journey = await agent.create_journey(
        title="查询预订状态",
        description="Retrieves the customer's booking status and provides relevant information.",
        conditions=["客户想要查询预订状态"],
    )

    t0 = await journey.initial_state.transition_to(
        chat_state="询问确认号或预订参考号"
    )

    t1 = await t0.target.transition_to(tool_state=get_booking_status)

    await t1.target.transition_to(
        chat_state="告知客户找不到预订信息，请他们核实确认号或致电办公室",
        condition="找不到预订信息",
    )

    await t1.target.transition_to(
        chat_state="提供预订详情并确认一切正常",
        condition="预订已确认且所有信息都正确",
    )

    await t1.target.transition_to(
        chat_state="展示预订信息并提及任何问题或所需的待处理操作",
        condition="预订存在问题或需要客户操作",
    )

    # 处理边缘情况故意使用指南
    # 例如，客户想要修改预订

    await journey.create_guideline(
        condition="客户想要修改预订",
        action="解释改签政策，并引导他们致电我们的办公室以获得修改协助",
    )

    await journey.create_guideline(
        condition="客户担心可能需要取消预订",
        action="提供我们的取消政策，并建议他们致电办公室讨论相关选项",
    )

    return journey


async def configure_container(container: p.Container) -> p.Container:
    container[p.PerceivedPerformancePolicy] = p.VoiceOptimizedPerceivedPerformancePolicy()
    return container


async def main() -> None:
    load_dotenv()
    async with p.Server(
        nlp_service=p.NLPServices.glm,
        configure_container=configure_container,
    ) as server:
        agent = await server.create_agent(
            name="小游",
            description="是一位经验丰富的旅行顾问，帮助客户预订航班、解答旅行问题和管理预订。",
        )

        await add_domain_glossary(agent)

        await create_flight_booking_journey(server, agent)
        await create_booking_status_journey(server, agent)

        await agent.create_guideline(
            condition="客户询问旅行保险",
            action="解释我们的旅行保险选项、保障详情和价格，然后提供将其添加到预订中",
        )

        await agent.create_guideline(
            condition="客户询问酒店或租车选项",
            action="告知他们我们可以帮助提供完整的旅行套餐，并建议他们致电我们的办公室或访问我们的网站进行酒店和租车预订",
        )

        await agent.create_guideline(
            condition="客户要求与人工客服通话",
            action="提供办公室电话号码和办公时间，并在此期间提供其他帮助",
        )

        await agent.create_guideline(
            condition="客户询问与预订旅行无关的目的地或活动",
            action="认可他们的兴趣，但解释您专注于旅行预订，并温和地引导他们了解您如何帮助他们的旅行计划",
        )

        await agent.create_guideline(
            condition="客户询问与旅行无关的事情",
            action="礼貌地告诉他们您无法协助与主题无关的询问 - 不要参与他们的请求。",
        )


if __name__ == "__main__":
    asyncio.run(main())
