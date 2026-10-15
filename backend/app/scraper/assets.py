from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ParsedScript:
    src: Optional[str] = None
    is_inline: bool = False
    content: str = ""
    is_blocking: bool = True
    is_defer: bool = False
    is_async: bool = False
    is_module: bool = False
    size_bytes: int = 0


@dataclass
class ParsedImage:
    src: str = ""
    is_data_uri: bool = False
    width: Optional[str] = None
    height: Optional[str] = None
    has_dimensions: bool = False
    is_lazy: bool = False
    alt: Optional[str] = None
    size_bytes: int = 0


@dataclass
class ParsedStylesheet:
    href: Optional[str] = None
    is_inline: bool = False
    content: str = ""
    size_bytes: int = 0
    is_render_blocking: bool = True
    imports: List[str] = field(default_factory=list)


@dataclass
class ParsedFont:
    href: Optional[str] = None
    source: str = "link"  # "link", "css", "preload"
    family: Optional[str] = None


@dataclass
class ParsedPreload:
    href: str
    as_type: str = "script"  # script, style, font, image
