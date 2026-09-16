cloak_add_library(
    NAME transport
    SOURCES
        tcp_transport.cpp
        mailbox_transport.cpp
        relay_transport.cpp
    DEPS
        core
        Boost::boost
        $<$<PLATFORM_ID:Windows>:ws2_32>
)
