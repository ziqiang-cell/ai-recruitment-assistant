"""仅使用 Mock 客户端及 SimpleNamespace 响应；不是实际 SDK/API 验证。"""

from copy import deepcopy
import inspect
import json
import os
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import agent_tools
from function_calling import run_single_tool_turn
from llm_tool_adapter import make_request_completion


def sdk_call(name=agent_tools.TOOL_NAME, arguments='{"query":"Python"}', call_id="call_sdk_001"):
    return SimpleNamespace(id=call_id, type="function",
                           function=SimpleNamespace(name=name, arguments=arguments))


def sdk_response(content="虚构回答", calls=None, reason="stop", **extra):
    message = SimpleNamespace(role="assistant", content=content, tool_calls=calls,
                              refusal=None, reasoning_content=None, function_call=None)
    for key, value in extra.items():
        setattr(message, key, value)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=reason)])


def sdk_tool_response(**kwargs):
    return sdk_response(content=None, calls=[sdk_call(**kwargs)], reason="tool_calls")


def mock_client():
    client = Mock(spec=["max_retries", "chat", "copy", "with_options", "close"])
    client.max_retries = 0
    client.chat.completions.create.return_value = sdk_response()
    return client


def tool_result():
    return {"ok": True, "results": [{"text": "虚构标准：Python 基础。",
            "source": "fictional_standard.md", "chunk_index": 0, "distance": 0.25}],
            "count": 1, "error": None}


class AdapterFactoryTests(unittest.TestCase):
    def test_factory_returns_callable_without_request(self):
        client = mock_client()
        self.assertTrue(callable(make_request_completion(client)))
        client.chat.completions.create.assert_not_called()
        client.with_options.assert_not_called()
        client.copy.assert_not_called()
        client.close.assert_not_called()

    def test_missing_or_incompatible_client_is_rejected(self):
        for client in [None, object(), SimpleNamespace(max_retries=0),
                       SimpleNamespace(max_retries=0, chat=SimpleNamespace(completions=SimpleNamespace(create=None)))]:
            with self.subTest(client_type=str(type(client))):
                with self.assertRaises(ValueError):
                    make_request_completion(client)

    def test_retries_must_be_integer_zero(self):
        client = mock_client()
        for value in [None, True, False, 0.0, "0", -1, 1, 2]:
            with self.subTest(value=value):
                client.max_retries = value
                with self.assertRaises(ValueError):
                    make_request_completion(client)
        client.chat.completions.create.assert_not_called()

    def test_async_client_is_rejected_without_creating_coroutine(self):
        client = mock_client()
        async def create(**kwargs):
            return sdk_response()
        client.chat.completions.create = create
        with self.assertRaises(ValueError):
            make_request_completion(client)

    def test_model_validation(self):
        client = mock_client()
        for value in [None, True, [], "", " \n ", "m" * 129]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    make_request_completion(client, model=value)
        self.assertTrue(callable(make_request_completion(client, model="m" * 128)))
        client.chat.completions.create.assert_not_called()

    def test_timeout_validation_including_nonfinite_and_huge_int(self):
        client = mock_client()
        for value in [None, True, False, "30", [], 0, -1, 121, float("nan"), float("inf"), float("-inf"), 10**400]:
            with self.subTest(value_type=str(type(value))):
                with self.assertRaises(ValueError):
                    make_request_completion(client, timeout=value)
        for value in [0.1, 30, 120]:
            self.assertTrue(callable(make_request_completion(client, timeout=value)))
        client.chat.completions.create.assert_not_called()

    def test_max_tokens_bounds_and_boolean_rejection(self):
        client = mock_client()
        for value in [None, True, False, "1024", 1.0, 0, -1, 4097]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    make_request_completion(client, max_tokens=value)
        for value in [1, 4096]:
            self.assertTrue(callable(make_request_completion(client, max_tokens=value)))
        client.chat.completions.create.assert_not_called()

    def test_keyword_only_configuration_and_callback(self):
        self.assertEqual(str(inspect.signature(make_request_completion)),
                         "(client, *, model='deepseek-flash', timeout=30.0, max_tokens=1024)")
        requester = make_request_completion(mock_client())
        self.assertEqual(str(inspect.signature(requester)), "(*, messages, tools, tool_choice)")
        with self.assertRaises(TypeError):
            make_request_completion(mock_client(), "model")


class AdapterRequestTests(unittest.TestCase):
    def setUp(self):
        self.client = mock_client()
        self.create = self.client.chat.completions.create
        self.requester = make_request_completion(self.client)
        self.messages = [{"role": "user", "content": "虚构问题"}]
        self.tools = agent_tools.get_tool_definitions()

    def call(self, **overrides):
        args = {"messages": self.messages, "tools": self.tools, "tool_choice": "auto"}
        args.update(overrides)
        return self.requester(**args)

    def test_defaults_are_explicit_and_do_not_force_json_output(self):
        self.assertEqual(self.call(), {"role": "assistant", "content": "虚构回答"})
        self.create.assert_called_once_with(
            model="deepseek-flash", messages=self.messages, tools=self.tools,
            tool_choice="auto", stream=False, n=1, timeout=30.0, max_tokens=1024,
            extra_body={"thinking": {"type": "disabled"}})
        self.assertNotIn("response_format", self.create.call_args.kwargs)

    def test_custom_configuration_and_none_choice(self):
        self.requester = make_request_completion(self.client, model=" local-test-model ", timeout=0.5, max_tokens=1)
        self.call(tool_choice="none")
        kwargs = self.create.call_args.kwargs
        self.assertEqual((kwargs["model"], kwargs["timeout"], kwargs["max_tokens"], kwargs["tool_choice"]),
                         ("local-test-model", 0.5, 1, "none"))

    def test_invalid_request_parameters_never_call_create(self):
        cases = [{"messages": None}, {"messages": []}, {"messages": "x"},
                 {"tools": None}, {"tools": []}, {"tools": {}},
                 {"tool_choice": "required"}, {"tool_choice": {}}, {"tool_choice": None}]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                with self.assertRaisesRegex(RuntimeError, "模型 SDK 请求或响应无效"):
                    self.call(**arguments)
        self.create.assert_not_called()

    def test_non_json_input_never_calls_create(self):
        for value in [object(), float("nan"), float("inf")]:
            with self.subTest(value_type=str(type(value))):
                with self.assertRaises(RuntimeError):
                    self.call(messages=[{"role": "user", "content": value}])
        self.create.assert_not_called()

    def test_request_uses_copies_not_caller_lists(self):
        original_messages = deepcopy(self.messages)
        original_tools = deepcopy(self.tools)
        def create(**kwargs):
            kwargs["messages"][0]["content"] = "SDK-shaped mock mutation"
            kwargs["tools"][0]["function"]["parameters"]["properties"].clear()
            return sdk_response()
        self.create.side_effect = create
        self.call()
        self.assertEqual(self.messages, original_messages)
        self.assertEqual(self.tools, original_tools)

    def test_retries_changed_after_factory_prevents_request(self):
        self.client.max_retries = 2
        with self.assertRaises(RuntimeError):
            self.call()
        self.create.assert_not_called()
        self.assertEqual(self.client.max_retries, 2)

    def test_no_client_copy_close_or_configuration_mutation(self):
        self.call()
        self.assertEqual(self.client.max_retries, 0)
        self.client.copy.assert_not_called()
        self.client.with_options.assert_not_called()
        self.client.close.assert_not_called()

    def test_no_credentials_or_sdk_construction(self):
        fake_sdk = ModuleType("openai")
        fake_sdk.OpenAI = Mock(side_effect=AssertionError("SDK construction forbidden"))
        with patch.dict(sys.modules, {"openai": fake_sdk}), \
                patch.object(os, "getenv", side_effect=AssertionError("Credential read forbidden")), \
                patch("builtins.open", side_effect=AssertionError("File reads forbidden")):
            self.assertEqual(self.call()["role"], "assistant")
        fake_sdk.OpenAI.assert_not_called()
        self.create.assert_called_once()


class AdapterResponseTests(unittest.TestCase):
    def setUp(self):
        self.client = mock_client()
        self.create = self.client.chat.completions.create
        self.requester = make_request_completion(self.client)

    def call(self):
        return self.requester(messages=[{"role": "user", "content": "虚构问题"}],
                              tools=agent_tools.get_tool_definitions(), tool_choice="auto")

    def assert_invalid(self, response):
        self.create.return_value = response
        with self.assertRaisesRegex(RuntimeError, "^模型 SDK 请求或响应无效。$") as error:
            self.call()
        self.assertIsNone(error.exception.__cause__)
        self.create.reset_mock()

    def test_plain_answer_drops_unneeded_sdk_fields(self):
        self.create.return_value = sdk_response(content="完整虚构回答", annotations=["synthetic"], audio="unused")
        self.assertEqual(self.call(), {"role": "assistant", "content": "完整虚构回答"})

    def test_tool_call_preserves_arguments_string_and_id(self):
        arguments = '{"query":"  Python  ","top_k":1}'
        self.create.return_value = sdk_tool_response(arguments=arguments)
        result = self.call()
        self.assertEqual(result, {"role": "assistant", "content": None, "tool_calls": [{
            "id": "call_sdk_001", "type": "function", "function": {
                "name": agent_tools.TOOL_NAME, "arguments": arguments}}]})
        json.dumps(result, allow_nan=False)

    def test_all_calls_are_preserved_for_existing_limit_check(self):
        self.create.return_value = sdk_response(content="准备检索", calls=[sdk_call(call_id="a"), sdk_call(call_id="b")], reason="tool_calls")
        result = self.call()
        self.assertEqual([c["id"] for c in result["tool_calls"]], ["a", "b"])
        self.assertEqual(result["content"], "准备检索")

    def test_empty_missing_non_list_or_multiple_choices(self):
        for response in [None, {}, SimpleNamespace(), SimpleNamespace(choices=None),
                         SimpleNamespace(choices=[]), SimpleNamespace(choices="x"),
                         SimpleNamespace(choices=[sdk_response().choices[0]] * 2)]:
            with self.subTest(response_type=str(type(response))):
                self.assert_invalid(response)

    def test_truncated_filtered_legacy_unknown_or_missing_finish_reason(self):
        for reason in ["length", "content_filter", "function_call", "aborted", "insufficient_system_resource", None, ""]:
            with self.subTest(reason=reason):
                self.assert_invalid(sdk_response(content="看似完整的虚构回答", reason=reason))

    def test_wrong_role_or_content_type(self):
        for extra in [{"role": "user"}, {"role": None}, {"content": 5}, {"content": []}]:
            with self.subTest(extra=extra):
                self.assert_invalid(sdk_response(**extra))

    def test_stop_requires_nonempty_content_and_no_calls(self):
        for content in [None, "", " \n "]:
            self.assert_invalid(sdk_response(content=content))
        self.assert_invalid(sdk_response(calls=[sdk_call()]))

    def test_tool_calls_reason_requires_nonempty_list(self):
        for calls in [None, [], "not-list", {}, (sdk_call(),)]:
            with self.subTest(calls_type=str(type(calls))):
                self.assert_invalid(sdk_response(content=None, calls=calls, reason="tool_calls"))

    def test_refusal_and_thinking_messages_are_rejected(self):
        for extra in [{"refusal": "synthetic refusal"}, {"reasoning_content": "synthetic reasoning"}, {"refusal": False}]:
            self.assert_invalid(sdk_response(**extra))
        self.create.return_value = sdk_response(refusal="", reasoning_content="")
        self.assertEqual(self.call()["content"], "虚构回答")

    def test_deprecated_function_call_is_rejected(self):
        for value in [{}, SimpleNamespace(name="legacy"), "legacy"]:
            self.assert_invalid(sdk_response(function_call=value))

    def test_invalid_call_type_id_and_function_fields(self):
        invalid = [None, SimpleNamespace(), sdk_call(call_id=""), sdk_call(call_id=" "),
                   sdk_call(call_id=5), sdk_call(call_id="x" * 201),
                   sdk_call(name=None), sdk_call(name=[]), sdk_call(arguments={}), sdk_call(arguments=None)]
        bad_type = sdk_call(); bad_type.type = "custom"; invalid.append(bad_type)
        bad_function = sdk_call(); bad_function.function = None; invalid.append(bad_function)
        for call in invalid:
            with self.subTest(call_type=str(type(call))):
                self.assert_invalid(sdk_response(content=None, calls=[call], reason="tool_calls"))

    def test_unknown_tool_and_bad_json_are_forwarded_without_execution(self):
        self.create.return_value = sdk_tool_response(name="unknown", arguments="bad JSON")
        result = self.call()
        self.assertEqual(result["tool_calls"][0]["function"], {"name": "unknown", "arguments": "bad JSON"})

    def test_mock_timeout_auth_rate_limit_and_connection_errors_never_retry(self):
        class MockAuthenticationError(Exception):
            pass
        class MockRateLimitError(Exception):
            pass
        for kind in [TimeoutError, MockAuthenticationError, MockRateLimitError, ConnectionError]:
            with self.subTest(error_type=kind.__name__):
                self.create.reset_mock()
                self.create.side_effect = kind("synthetic-private-detail")
                with self.assertRaises(RuntimeError) as error:
                    self.call()
                self.assertNotIn("private", str(error.exception))
                self.assertEqual(str(error.exception), "模型 SDK 请求或响应无效。")
                self.create.assert_called_once()


class AdapterBridgeTests(unittest.TestCase):
    def setUp(self):
        self.client = mock_client()
        self.create = self.client.chat.completions.create
        self.requester = make_request_completion(self.client)
        self.execute = self.enterContext(patch("agent_tools._execute_search", return_value=tool_result()))

    def test_complete_sdk_shaped_round_trip(self):
        self.create.side_effect = [sdk_tool_response(), sdk_response(content="依据 fictional_standard.md，学习 Python。")]
        result = run_single_tool_turn("Python", self.requester)
        self.assertTrue(result["ok"])
        self.assertEqual(result["tool_result"], tool_result())
        self.assertEqual(self.create.call_count, 2)
        self.execute.assert_called_once_with({"query": "Python"})
        first, second = [c.kwargs for c in self.create.call_args_list]
        self.assertEqual(first["tool_choice"], "auto")
        self.assertEqual(second["tool_choice"], "none")
        self.assertEqual(second["messages"][-1]["tool_call_id"], "call_sdk_001")
        self.assertEqual(json.loads(second["messages"][-1]["content"]), tool_result())
        json.dumps(result, allow_nan=False)

    def test_direct_answer_uses_one_request_and_no_tool(self):
        self.create.return_value = sdk_response(content="你好，本次未检索。")
        self.assertTrue(run_single_tool_turn("你好", self.requester)["ok"])
        self.create.assert_called_once()
        self.execute.assert_not_called()

    def test_tool_failure_stops_second_request(self):
        self.create.return_value = sdk_tool_response()
        self.execute.return_value = {"ok": False, "results": [], "count": 0,
                                     "error": {"code": "RETRIEVAL_ERROR", "message": "检索失败。"}}
        result = run_single_tool_turn("Python", self.requester)
        self.assertEqual(result["error"]["code"], "TOOL_FAILED")
        self.assertIsNone(result["answer"])
        self.create.assert_called_once()
        self.execute.assert_called_once()

    def test_first_request_error_stops_without_tool(self):
        self.create.side_effect = TimeoutError("synthetic-private-detail")
        result = run_single_tool_turn("Python", self.requester)
        self.assertEqual(result["error"]["code"], "MODEL_REQUEST_ERROR")
        self.assertNotIn("private", json.dumps(result))
        self.create.assert_called_once()
        self.execute.assert_not_called()

    def test_second_request_error_preserves_evidence(self):
        self.create.side_effect = [sdk_tool_response(), ConnectionError("synthetic-private-detail")]
        result = run_single_tool_turn("Python", self.requester)
        self.assertEqual(result["error"]["code"], "MODEL_REQUEST_ERROR")
        self.assertEqual(result["tool_result"], tool_result())
        self.assertEqual(self.create.call_count, 2)
        self.execute.assert_called_once()

    def test_multiple_calls_are_rejected_before_tool_execution(self):
        self.create.return_value = sdk_response(content=None, calls=[sdk_call(call_id="a"), sdk_call(call_id="b")], reason="tool_calls")
        result = run_single_tool_turn("Python", self.requester)
        self.assertEqual(result["error"]["code"], "TOOL_CALL_LIMIT")
        self.create.assert_called_once()
        self.execute.assert_not_called()

    def test_unknown_tool_bad_json_and_extra_paths_stop_locally(self):
        for kwargs, code in [({"name": "rebuild_knowledge_base"}, "UNKNOWN_TOOL"),
                             ({"arguments": "bad JSON"}, "INVALID_ARGUMENTS"),
                             ({"arguments": '{"query":"Python","database_path":"fictional"}'}, "INVALID_ARGUMENTS")]:
            with self.subTest(code=code):
                self.create.reset_mock()
                self.create.return_value = sdk_tool_response(**kwargs)
                result = run_single_tool_turn("Python", self.requester)
                self.assertEqual(result["error"]["code"], "TOOL_FAILED")
                self.assertEqual(result["tool_result"]["error"]["code"], code)
                self.create.assert_called_once()
        self.execute.assert_not_called()

    def test_truncated_first_response_never_executes_tool(self):
        response = sdk_tool_response(); response.choices[0].finish_reason = "length"
        self.create.return_value = response
        result = run_single_tool_turn("Python", self.requester)
        self.assertEqual(result["error"]["code"], "MODEL_REQUEST_ERROR")
        self.create.assert_called_once()
        self.execute.assert_not_called()

    def test_truncated_final_response_does_not_become_success(self):
        self.create.side_effect = [sdk_tool_response(), sdk_response(content="看似完整的虚构回答", reason="length")]
        result = run_single_tool_turn("Python", self.requester)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["answer"])
        self.assertEqual(result["tool_result"], tool_result())
        self.assertEqual(self.create.call_count, 2)
        self.execute.assert_called_once()

    def test_retry_configuration_changed_between_rounds_stops_next_create(self):
        self.create.return_value = sdk_tool_response()
        def execute(arguments):
            self.client.max_retries = 2
            return tool_result()
        self.execute.side_effect = execute
        result = run_single_tool_turn("Python", self.requester)
        self.assertEqual(result["error"]["code"], "MODEL_REQUEST_ERROR")
        self.assertEqual(result["tool_result"], tool_result())
        self.create.assert_called_once()
        self.execute.assert_called_once()

    def test_second_tool_call_is_not_executed(self):
        self.create.side_effect = [sdk_tool_response(), sdk_tool_response()]
        result = run_single_tool_turn("Python", self.requester)
        self.assertEqual(result["error"]["code"], "TOOL_CALL_LIMIT")
        self.assertEqual(self.create.call_count, 2)
        self.execute.assert_called_once()

    def test_empty_results_stay_empty(self):
        self.execute.return_value = {"ok": True, "results": [], "count": 0, "error": None}
        self.create.side_effect = [sdk_tool_response(), sdk_response(content="未检索到相关标准。")]
        result = run_single_tool_turn("Python", self.requester)
        self.assertTrue(result["ok"])
        self.assertEqual(result["tool_result"]["results"], [])
        self.assertEqual(json.loads(self.create.call_args.kwargs["messages"][-1]["content"])["count"], 0)


if __name__ == "__main__":
    unittest.main()
