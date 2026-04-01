# Reasoning

Here are the pros and cons considered when switching the backend from
Connexion/Flask to FastAPI:

## Pros

* **Automatic docs**: Swagger UI and ReDoc generated from your code with zero config
* **Native async**: built on Starlette/ASGI, first-class async/await support
* **Type-driven validation**: Pydantic models give you request/response validation and serialization for free
* **Performance**: significantly faster than Flask for I/O-bound workloads due to async
* **Modern Python**: designed around type hints, feels natural with Python 3.9+
* **Fast development**: less boilerplate for standard REST or ML-serving APIs

## Cons

* **Pydantic coupling**: you're heavily tied to Pydantic; v1→v2 migration was painful for many
* **Younger ecosystem**: fewer mature extensions compared to Flask
* **Async complexity**: if your team isn't comfortable with async/await, bugs can be subtle (e.g. accidentally blocking the event loop)
* **Less flexible for non-standard patterns**: Flask's minimalism can be easier to bend for unusual architectures
* **OpenAPI spec is derived, not primary**: if you need spec-first design (e.g. contract-first with other teams), Connexion's approach is more natural
