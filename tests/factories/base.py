from typing import Any, Generic, TypeVar
from uuid import UUID

import factory
from factory.django import DjangoModelFactory

T = TypeVar("T")


class BaseFactory(DjangoModelFactory, Generic[T]):
    id = factory.Sequence(lambda n: UUID(int=n))

    @classmethod
    def create(cls, **kwargs: Any) -> T:
        return super().create(**kwargs)

    @classmethod
    def create_batch(cls, size: int, **kwargs: Any) -> list[T]:
        return super().create_batch(size, **kwargs)
