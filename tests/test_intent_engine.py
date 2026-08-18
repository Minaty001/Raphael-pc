from raphael.brain.intent import IntentEngine, IntentType

def test_intent_classification():
    ie = IntentEngine()

    res_open = ie.classify("open Chrome")
    assert res_open["intent"] == IntentType.OPEN_APP
    assert res_open["args"]["app_name"] == "chrome"

    res_status = ie.classify("show system info")
    assert res_status["intent"] == IntentType.SYSTEM_STATUS

    res_screenshot = ie.classify("take screenshot")
    assert res_screenshot["intent"] == IntentType.TAKE_SCREENSHOT

    res_chat = ie.classify("tell me a story about space")
    assert res_chat["intent"] == IntentType.GENERAL_CHAT
