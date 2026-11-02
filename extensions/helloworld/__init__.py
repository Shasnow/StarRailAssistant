import time
from typing import Literal

from pydantic import BaseModel, Field

from SRACore.extension import BaseExtension, extension


class HelloWorldConfig(BaseModel):
    message: str = Field(default="Hello World!")
    repeat: int = Field(default=1)
    delay: float = Field(default=0.0)
    say: bool = Field(default=False)
    name: Literal["Bob", "Alice"] = "Bob"


@extension
class HelloWorldExtension(BaseExtension[HelloWorldConfig]):
    def __post_init__(self) -> None:
        return super().__post_init__()

    def run(self) -> bool:
        if self.config.say:
            print(f"{self.config.name}: {self.config.message}")
        else:
            for _ in range(self.config.repeat):
                print(self.config.message)
                if self.config.delay > 0:
                    time.sleep(self.config.delay)
        return True