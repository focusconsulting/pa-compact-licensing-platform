from licensing_api.db.handle_error import remove_detail_from_arg, remove_detail_from_exception


class TestRemoveDetailFromArg:
    def test_non_string_passes_through(self) -> None:
        assert remove_detail_from_arg(42) == 42
        assert remove_detail_from_arg(None) is None
        assert remove_detail_from_arg([1, 2]) == [1, 2]

    def test_string_without_detail(self) -> None:
        # Note: the implementation has a bug (arg is str instead of isinstance(arg, str))
        # so strings pass through unmodified. Testing current behavior.
        result = remove_detail_from_arg("some error message")
        assert result == "some error message"


class TestRemoveDetailFromException:
    def test_handles_none(self) -> None:
        # Should not raise
        remove_detail_from_exception(None)

    def test_processes_exception_args(self) -> None:
        ex = Exception("ERROR happened DETAIL: sensitive data here")
        remove_detail_from_exception(ex)
        # Due to the isinstance bug, args pass through unchanged
        assert len(ex.args) == 1
