#include <cloak/relay/relay_server.h>

#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#else
#include <csignal>
#include <cstdlib>
#endif
#include <boost/program_options.hpp>
#include <iostream>
#include <memory>

namespace po = boost::program_options;

static std::unique_ptr<cloak::relay::RelayServer> g_relay;

#if defined(_WIN32)
BOOL WINAPI CtrlHandler(DWORD fdwCtrlType) {
    if (fdwCtrlType == CTRL_C_EVENT || fdwCtrlType == CTRL_CLOSE_EVENT) {
        std::cout << "\n[cloak-relay] Shutting down.\n";
        if (g_relay) g_relay->stop();
        ExitProcess(0);
    }
    return FALSE;
}
#else
void CtrlHandler(int) {
    std::cout << "\n[cloak-relay] Shutting down.\n";
    if (g_relay) g_relay->stop();
    std::exit(0);
}
#endif

int main(int argc, char** argv) {
#if defined(_WIN32)
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCtrlHandler(CtrlHandler, TRUE);
#else
    std::signal(SIGINT, CtrlHandler);
    std::signal(SIGTERM, CtrlHandler);
#endif

    po::options_description desc("cloak-relay options");
    desc.add_options()
        ("help",  "show this help")
        ("port",  po::value<uint16_t>()->default_value(8765),
                  "TCP port to listen on (default: 8765)");

    po::variables_map vm;
    try {
        po::store(po::parse_command_line(argc, argv, desc), vm);
        po::notify(vm);
    } catch (const po::error& e) {
        std::cerr << "Argument error: " << e.what() << "\n";
        return 1;
    }

    if (vm.count("help")) {
        std::cout << "cloak-relay 0.4.0 — Cloak relay server\n\n" << desc << "\n";
        return 0;
    }

    const uint16_t port = vm["port"].as<uint16_t>();

    g_relay = std::make_unique<cloak::relay::RelayServer>(port);
    std::cout << "cloak-relay 0.4.0  |  listening on port " << port << "\n"
              << "Press Ctrl+C to stop.\n";

    auto result = g_relay->run();
    if (!result) {
        std::cerr << "[Fatal] " << result.error().message << "\n";
        return 2;
    }
    return 0;
}
