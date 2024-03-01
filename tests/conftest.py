from sanic import Sanic

Sanic.test_mode = True


def get_stack():
    dialogue_stack = [
        {
            "frame_id": "CP6JP9GQ",
            "flow_id": "check_balance",
            "step_id": "0_check_balance",
            "frame_type": "regular",
            "type": "flow",
        }
    ]
    return dialogue_stack
