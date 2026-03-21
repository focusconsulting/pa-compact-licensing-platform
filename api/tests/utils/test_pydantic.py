from licensing_api.utils.pydantic import PydanticBaseModel


class TestPydanticBaseModel:
    def test_camel_case_serialization(self) -> None:
        class MyModel(PydanticBaseModel):
            first_name: str
            last_name: str

        model = MyModel(first_name="John", last_name="Doe")
        dumped = model.model_dump(by_alias=True)
        assert "firstName" in dumped
        assert "lastName" in dumped
        assert dumped["firstName"] == "John"

    def test_from_attributes(self) -> None:
        class MyModel(PydanticBaseModel):
            some_field: str

        model = MyModel(some_field="test")
        assert model.some_field == "test"

    def test_populate_by_name(self) -> None:
        class MyModel(PydanticBaseModel):
            some_field: str

        model = MyModel(**{"some_field": "test"})
        assert model.some_field == "test"
