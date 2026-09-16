cloak_add_library(
    NAME wire
    SOURCES
        framing.cpp
    DEPS
        core
        $<$<PLATFORM_ID:Windows>:ws2_32>
)
