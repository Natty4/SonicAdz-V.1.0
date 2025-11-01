from user_agents import parse as parse_ua

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')

def get_device_info(request):
    user_agent_str = get_user_agent(request)
    user_agent = parse_ua(user_agent_str)

    return {
        "user_agent_str": user_agent_str,
        "is_mobile": user_agent.is_mobile,
        "is_tablet": user_agent.is_tablet,
        "is_pc": user_agent.is_pc,
        "is_bot": user_agent.is_bot,
        "os": user_agent.os.family,
        "browser": user_agent.browser.family,
        "device": user_agent.device.family,
    }