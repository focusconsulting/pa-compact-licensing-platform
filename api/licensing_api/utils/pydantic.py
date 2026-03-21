from pydantic import AliasGenerator, BaseModel
from pydantic.alias_generators import to_camel


class PydanticBaseModel(BaseModel):
    model_config = {
        "from_attributes": True,
        "alias_generator": AliasGenerator(serialization_alias=to_camel),
        "populate_by_name": True,
    }
