// chat_ui.cpp — Full FTXUI button-driven UI for Cloak.

#include <cloak/ui/chat_ui.h>
#include <cloak/app/chat_application.h>

#include <ftxui/component/component.hpp>
#include <ftxui/component/component_options.hpp>
#include <ftxui/component/screen_interactive.hpp>
#include <ftxui/dom/elements.hpp>
#include <ftxui/screen/color.hpp>

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>

#include <cstring>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace cloak::ui {

using namespace ftxui;

// ── Win32 Clipboard helpers ───────────────────────────────────────────────────

static std::string clip_get() {
    if (!OpenClipboard(nullptr)) return {};
    std::string result;
    HANDLE h = GetClipboardData(CF_TEXT);
    if (h) {
        const char* data = static_cast<const char*>(GlobalLock(h));
        if (data) result = data;
        GlobalUnlock(h);
    }
    CloseClipboard();
    // Strip \r so Windows line endings don't break inputs.
    std::string clean;
    clean.reserve(result.size());
    for (char c : result) if (c != '\r') clean += c;
    return clean;
}

static void clip_set(const std::string& text) {
    if (!OpenClipboard(nullptr)) return;
    EmptyClipboard();
    HGLOBAL h = GlobalAlloc(GMEM_MOVEABLE, text.size() + 1);
    if (h) {
        char* data = static_cast<char*>(GlobalLock(h));
        if (data) {
            std::memcpy(data, text.c_str(), text.size() + 1);
            GlobalUnlock(h);
            SetClipboardData(CF_TEXT, h);
        }
    }
    CloseClipboard();
}

// Wrap a component so Ctrl+V (ASCII 0x16) pastes from clipboard into *target.
static Component with_paste(Component inner, std::string* target) {
    return CatchEvent(inner, [target](Event e) -> bool {
        if (e == Event::Character('\x16')) {
            std::string clip = clip_get();
            if (!clip.empty()) *target += clip;
            return true;
        }
        return false;
    });
}

// Format a 60-digit safety number into two display rows (3 groups of 10 each).
static std::string sn_row(const std::string& digits, size_t start) {
    if (digits.size() < start + 30) return {};
    return digits.substr(start, 10) + "   " +
           digits.substr(start + 10, 10) + "   " +
           digits.substr(start + 20, 10);
}

// ── ChatUi ───────────────────────────────────────────────────────────────────

ChatUi::ChatUi(cloak::app::ChatApplication& app) : app_(app) {}

void ChatUi::request_shutdown() { shutdown_ = true; }

cloak::core::Result<void> ChatUi::run_main_loop() {
    auto screen = ScreenInteractive::Fullscreen();

    // ── Shared state (written by background threads, read by renderer) ─────────
    std::mutex                                              state_mutex;
    std::vector<cloak::app::ChatApplication::MessageEntry> messages;
    std::vector<cloak::app::ChatApplication::PeerInfo>     peers;
    std::vector<cloak::app::ChatApplication::GroupEntry>   groups;
    std::string                                             status_line = "Ready";
    std::string                                             invite_code_str;

    // ── UI-thread-only state ───────────────────────────────────────────────────
    std::string  input_text;
    std::string  join_code_input;
    std::string  direct_host_input;
    std::string  direct_port_input;
    std::string  new_group_name_input;
    std::string  file_path_input;
    std::string  safety_line1;
    std::string  safety_line2;

    bool  show_invite_modal  = false;
    bool  show_join_modal    = false;
    bool  show_direct_modal  = false;
    bool  show_safety_modal  = false;
    bool  show_group_modal   = false;
    bool  show_file_modal    = false;
    bool  invite_generating  = false;

    int  peer_selected  = 0;
    int  group_selected = 0;

    // Tab: 0=main, 1=invite, 2=join, 3=direct, 4=safety, 5=group-create, 6=file-send
    int  active_tab = 0;

    std::vector<std::string> peer_entries;
    std::vector<std::string> group_entries;

    auto rebuild_peer_entries = [&](const std::vector<cloak::app::ChatApplication::PeerInfo>& ps) {
        peer_entries.clear();
        for (const auto& p : ps) {
            std::string label = (p.online ? " ● " : " ○ ") + p.name;
            if (p.verified)     label += " ✓";
            if (p.queued_count) label += " [" + std::to_string(p.queued_count) + "]";
            peer_entries.push_back(label);
        }
    };

    auto rebuild_group_entries = [&](const std::vector<cloak::app::ChatApplication::GroupEntry>& gs) {
        group_entries.clear();
        for (const auto& g : gs) {
            std::string label = (g.active ? " ● " : " ○ ") + g.name;
            group_entries.push_back(label);
        }
    };

    // ── Initial load ───────────────────────────────────────────────────────────
    {
        peers  = app_.get_peers();
        groups = app_.get_groups();
        rebuild_peer_entries(peers);
        rebuild_group_entries(groups);
    }

    // ── Callbacks from background threads ──────────────────────────────────────
    auto post_refresh = [&] { screen.PostEvent(Event::Custom); };

    app_.set_message_callback([&](std::string from, std::string text, bool is_mine) {
        {
            std::lock_guard lock(state_mutex);
            messages.push_back({from, text, "", is_mine});
        }
        post_refresh();
    });
    app_.set_peer_change_callback([&]() {
        {
            std::lock_guard lock(state_mutex);
            peers  = app_.get_peers();
            groups = app_.get_groups();
            rebuild_peer_entries(peers);
            rebuild_group_entries(groups);
        }
        post_refresh();
    });
    app_.set_system_callback([&](std::string msg) {
        {
            std::lock_guard lock(state_mutex);
            status_line = msg;
        }
        post_refresh();
    });

    // ── Components ─────────────────────────────────────────────────────────────

    // Message input + Send button.
    InputOption inp_opt;
    inp_opt.on_enter = [&] {
        if (input_text.empty()) return;
        std::string t = input_text; input_text.clear();
        std::thread([&, t]() { static_cast<void>(app_.send_text_to_current(t)); }).detach();
    };
    auto msg_input = with_paste(Input(&input_text, "Type a message...", inp_opt), &input_text);
    auto send_btn  = Button("  Send  ", [&] {
        if (input_text.empty()) return;
        std::string t = input_text; input_text.clear();
        std::thread([&, t]() { static_cast<void>(app_.send_text_to_current(t)); }).detach();
    }, ButtonOption::Ascii());

    // Group message send button.
    auto group_send_btn = Button(" Group Msg ", [&] {
        if (input_text.empty()) return;
        std::string t = input_text; input_text.clear();
        std::thread([&, t]() {
            auto res = app_.send_group_message(t);
            if (!res) {
                std::lock_guard lock(state_mutex);
                status_line = "Group send failed: " + res.error().message;
                post_refresh();
            }
        }).detach();
    }, ButtonOption::Ascii());

    // Left panel: connection buttons.
    auto search_btn = Button(" [◎] Search LAN ", [&] {
        {
            std::lock_guard lock(state_mutex);
            status_line = "Searching LAN...";
        }
        post_refresh();
        std::thread([&]() {
            std::this_thread::sleep_for(std::chrono::milliseconds(300));
            std::lock_guard lock(state_mutex);
            peers = app_.get_peers();
            rebuild_peer_entries(peers);
            status_line = peers.empty() ? "No peers found" :
                std::to_string(peers.size()) + " peer(s) found";
            post_refresh();
        }).detach();
    }, ButtonOption::Ascii());

    auto invite_btn = Button(" [✉] Invite Code ", [&] {
        show_invite_modal = true;
        active_tab        = 1;
        invite_generating = true;
        invite_code_str   = "Generating...";
        post_refresh();
        std::thread([&]() {
            auto res = app_.make_invite_code();
            {
                std::lock_guard lock(state_mutex);
                invite_generating = false;
                invite_code_str   = res ? *res : "[Error] " + res.error().message;
                status_line       = res ? "Invite code ready — share it!" : res.error().message;
            }
            post_refresh();
        }).detach();
    }, ButtonOption::Ascii());

    auto join_btn = Button(" [↪] Join via Code ", [&] {
        join_code_input   = "";
        show_join_modal   = true;
        active_tab        = 2;
        post_refresh();
    }, ButtonOption::Ascii());

    auto direct_btn = Button(" [➡] Direct Connect ", [&] {
        direct_host_input = "";
        direct_port_input = "";
        show_direct_modal = true;
        active_tab        = 3;
        post_refresh();
    }, ButtonOption::Ascii());

    // Safety number button.
    auto safety_btn = Button(" [⚿] Safety Number ", [&] {
        const std::string sn = app_.get_safety_number();
        if (sn.empty()) {
            std::lock_guard lock(state_mutex);
            status_line = "No active session — connect to a peer first";
            post_refresh();
            return;
        }
        if (sn.size() >= 60) {
            safety_line1 = sn_row(sn, 0);
            safety_line2 = sn_row(sn, 30);
        } else {
            safety_line1 = sn;
            safety_line2 = {};
        }
        show_safety_modal = true;
        active_tab        = 4;
        post_refresh();
    }, ButtonOption::Ascii());

    // Send file button.
    auto send_file_open_btn = Button(" [▶] Send File ", [&] {
        file_path_input = "";
        show_file_modal = true;
        active_tab      = 6;
        post_refresh();
    }, ButtonOption::Ascii());

    // Peer list menu.
    MenuOption menu_opt = MenuOption::Vertical();
    menu_opt.on_change = [&] {
        if (peer_selected >= 0)
            app_.switch_peer(static_cast<size_t>(peer_selected));
        std::lock_guard lock(state_mutex);
        messages.clear();
        status_line = peers.empty() ? "Ready" :
            "Chat with " + peers[static_cast<size_t>(peer_selected)].name;
        post_refresh();
    };
    auto peer_menu = Menu(&peer_entries, &peer_selected, menu_opt);

    // Group list menu.
    MenuOption group_menu_opt = MenuOption::Vertical();
    group_menu_opt.on_change = [&] {
        if (group_selected >= 0 && group_selected < static_cast<int>(groups.size()))
            static_cast<void>(app_.switch_group(static_cast<size_t>(group_selected)));
        post_refresh();
    };
    auto group_menu = Menu(&group_entries, &group_selected, group_menu_opt);

    // Group action buttons.
    auto create_group_btn = Button(" [+] Create Group ", [&] {
        new_group_name_input = "";
        show_group_modal     = true;
        active_tab           = 5;
        post_refresh();
    }, ButtonOption::Ascii());

    auto invite_group_btn = Button(" [→] Invite to Group ", [&] {
        std::thread([&]() {
            auto res = app_.invite_current_peer_to_group();
            std::lock_guard lock(state_mutex);
            if (res) {
                groups = app_.get_groups();
                rebuild_group_entries(groups);
                status_line = "Peer invited to group!";
            } else {
                status_line = "Invite failed: " + res.error().message;
            }
            post_refresh();
        }).detach();
    }, ButtonOption::Ascii());

    auto leave_group_btn = Button(" [x] Leave Group ", [&] {
        std::thread([&]() {
            auto res = app_.leave_group();
            std::lock_guard lock(state_mutex);
            groups = app_.get_groups();
            rebuild_group_entries(groups);
            status_line = res ? "Left group." : "Leave failed: " + res.error().message;
            post_refresh();
        }).detach();
    }, ButtonOption::Ascii());

    // Copy-address button.
    std::string copy_addr_label = " Copy Addr ";
    auto copy_addr_btn = Button(&copy_addr_label, [&] {
        const uint16_t    port = app_.my_listen_port();
        const std::string addr = app_.my_lan_ip() + ":" + std::to_string(port);
        clip_set(addr);
        copy_addr_label = " Copied! ✓ ";
        std::thread([&] {
            std::this_thread::sleep_for(std::chrono::seconds(2));
            copy_addr_label = " Copy Addr ";
            post_refresh();
        }).detach();
        post_refresh();
    }, ButtonOption::Ascii());

    // ── Invite modal components ────────────────────────────────────────────────
    std::string copy_code_label = "  Copy Code  ";
    auto copy_code_btn = Button(&copy_code_label, [&] {
        clip_set(invite_code_str);
        copy_code_label = "  Copied! ✓  ";
        std::thread([&] {
            std::this_thread::sleep_for(std::chrono::seconds(2));
            copy_code_label = "  Copy Code  ";
            post_refresh();
        }).detach();
        post_refresh();
    }, ButtonOption::Ascii());

    auto close_invite_btn = Button("  Close  ", [&] {
        show_invite_modal = false;
        active_tab        = 0;
        post_refresh();
    }, ButtonOption::Ascii());

    // ── Join modal components ──────────────────────────────────────────────────
    auto join_input = with_paste(
        Input(&join_code_input, "Type or paste invite code here..."),
        &join_code_input);

    auto connect_join_btn = Button("  Connect  ", [&] {
        if (join_code_input.empty()) return;
        std::string code = join_code_input;
        show_join_modal  = false;
        active_tab       = 0;
        join_code_input  = "";
        { std::lock_guard lock(state_mutex); status_line = "Connecting via invite..."; }
        post_refresh();
        std::thread([&, code]() {
            auto res = app_.connect_invite(code);
            std::lock_guard lock(state_mutex);
            status_line = res ? "Connected!" : "Connect failed: " + res.error().message;
            post_refresh();
        }).detach();
    }, ButtonOption::Ascii());

    auto cancel_join_btn = Button("  Cancel  ", [&] {
        show_join_modal = false;
        active_tab      = 0;
        post_refresh();
    }, ButtonOption::Ascii());

    // ── Direct connect modal components ───────────────────────────────────────
    auto host_input = with_paste(
        Input(&direct_host_input, "IP or hostname (e.g. 192.168.1.5)"),
        &direct_host_input);
    auto port_input = with_paste(
        Input(&direct_port_input, "Port (e.g. 5000)"),
        &direct_port_input);

    auto do_direct_btn = Button("  Connect  ", [&] {
        if (direct_host_input.empty() || direct_port_input.empty()) return;
        std::string host = direct_host_input;
        uint16_t    port = 0;
        try { port = static_cast<uint16_t>(std::stoi(direct_port_input)); }
        catch (...) {
            std::lock_guard lock(state_mutex);
            status_line = "Invalid port number";
            post_refresh();
            return;
        }
        show_direct_modal = false;
        active_tab        = 0;
        direct_host_input = "";
        direct_port_input = "";
        { std::lock_guard lock(state_mutex);
          status_line = "Connecting to " + host + ":" + std::to_string(port) + "..."; }
        post_refresh();
        std::thread([&, host, port]() {
            auto res = app_.connect_to(host, port);
            std::lock_guard lock(state_mutex);
            status_line = res ? "Connected!" : "Failed: " + res.error().message;
            post_refresh();
        }).detach();
    }, ButtonOption::Ascii());

    auto cancel_direct_btn = Button("  Cancel  ", [&] {
        show_direct_modal = false;
        active_tab        = 0;
        post_refresh();
    }, ButtonOption::Ascii());

    // ── Safety number modal components ────────────────────────────────────────
    auto verify_peer_btn = Button("  Mark Verified ✓  ", [&] {
        auto res = app_.verify_current_peer();
        show_safety_modal = false;
        active_tab        = 0;
        {
            std::lock_guard lock(state_mutex);
            peers = app_.get_peers();
            rebuild_peer_entries(peers);
            status_line = res ? "Peer marked as verified ✓" :
                                "Verify failed: " + res.error().message;
        }
        post_refresh();
    }, ButtonOption::Ascii());

    auto close_safety_btn = Button("  Close  ", [&] {
        show_safety_modal = false;
        active_tab        = 0;
        post_refresh();
    }, ButtonOption::Ascii());

    auto safety_modal_comp = Container::Vertical({
        Container::Horizontal({verify_peer_btn, close_safety_btn}),
    });

    // ── Create group modal components ─────────────────────────────────────────
    InputOption group_inp_opt;
    group_inp_opt.on_enter = [&] {
        if (new_group_name_input.empty()) return;
        std::string name = new_group_name_input;
        show_group_modal     = false;
        active_tab           = 0;
        new_group_name_input = "";
        std::thread([&, name]() {
            auto res = app_.create_group(name);
            std::lock_guard lock(state_mutex);
            groups = app_.get_groups();
            rebuild_group_entries(groups);
            status_line = res ? "Group '" + name + "' created ✓" :
                                "Create failed: " + res.error().message;
            post_refresh();
        }).detach();
    };
    auto group_name_input_comp = with_paste(
        Input(&new_group_name_input, "Group name (e.g. Team Alpha)", group_inp_opt),
        &new_group_name_input);

    auto create_group_confirm_btn = Button("  Create  ", [&] {
        if (new_group_name_input.empty()) return;
        std::string name = new_group_name_input;
        show_group_modal     = false;
        active_tab           = 0;
        new_group_name_input = "";
        std::thread([&, name]() {
            auto res = app_.create_group(name);
            std::lock_guard lock(state_mutex);
            groups = app_.get_groups();
            rebuild_group_entries(groups);
            status_line = res ? "Group '" + name + "' created ✓" :
                                "Create failed: " + res.error().message;
            post_refresh();
        }).detach();
    }, ButtonOption::Ascii());

    auto cancel_group_btn = Button("  Cancel  ", [&] {
        show_group_modal = false;
        active_tab       = 0;
        post_refresh();
    }, ButtonOption::Ascii());

    auto group_modal_comp = Container::Vertical({
        group_name_input_comp,
        Container::Horizontal({create_group_confirm_btn, cancel_group_btn}),
    });

    // ── File send modal components ─────────────────────────────────────────────
    InputOption file_inp_opt;
    file_inp_opt.on_enter = [&] {
        if (file_path_input.empty()) return;
        std::string path = file_path_input;
        show_file_modal = false;
        active_tab      = 0;
        file_path_input = "";
        { std::lock_guard lock(state_mutex); status_line = "Sending file..."; }
        post_refresh();
        std::thread([&, path]() {
            auto res = app_.send_file_to_current(path,
                [&](uint64_t sent, uint64_t total) {
                    const int pct = total > 0 ? static_cast<int>(sent * 100 / total) : 0;
                    std::lock_guard lock(state_mutex);
                    status_line = "Sending... " + std::to_string(pct) + "% (" +
                        std::to_string(sent) + "/" + std::to_string(total) + " B)";
                    post_refresh();
                });
            std::lock_guard lock(state_mutex);
            status_line = res ? "File sent successfully ✓" :
                                "Send failed: " + res.error().message;
            post_refresh();
        }).detach();
    };
    auto file_path_input_comp = with_paste(
        Input(&file_path_input, "Full path, e.g. C:\\Users\\...\\photo.png", file_inp_opt),
        &file_path_input);

    auto do_send_file_btn = Button("  Send File  ", [&] {
        if (file_path_input.empty()) return;
        std::string path = file_path_input;
        show_file_modal = false;
        active_tab      = 0;
        file_path_input = "";
        { std::lock_guard lock(state_mutex); status_line = "Sending file..."; }
        post_refresh();
        std::thread([&, path]() {
            auto res = app_.send_file_to_current(path,
                [&](uint64_t sent, uint64_t total) {
                    const int pct = total > 0 ? static_cast<int>(sent * 100 / total) : 0;
                    std::lock_guard lock(state_mutex);
                    status_line = "Sending... " + std::to_string(pct) + "% (" +
                        std::to_string(sent) + "/" + std::to_string(total) + " B)";
                    post_refresh();
                });
            std::lock_guard lock(state_mutex);
            status_line = res ? "File sent successfully ✓" :
                                "Send failed: " + res.error().message;
            post_refresh();
        }).detach();
    }, ButtonOption::Ascii());

    auto cancel_file_btn = Button("  Cancel  ", [&] {
        show_file_modal = false;
        active_tab      = 0;
        post_refresh();
    }, ButtonOption::Ascii());

    auto file_modal_comp = Container::Vertical({
        file_path_input_comp,
        Container::Horizontal({do_send_file_btn, cancel_file_btn}),
    });

    // ── Container assembly ─────────────────────────────────────────────────────
    auto left_panel_comp = Container::Vertical({
        search_btn, invite_btn, join_btn, direct_btn,
        safety_btn, send_file_open_btn,
        peer_menu,
        create_group_btn, invite_group_btn, leave_group_btn,
        group_menu,
        copy_addr_btn,
    });
    auto input_row = Container::Horizontal({msg_input, send_btn, group_send_btn});
    auto main_comp = Container::Horizontal({left_panel_comp, input_row});

    auto invite_modal_comp = Container::Vertical({
        copy_code_btn, close_invite_btn,
    });
    auto join_modal_comp = Container::Vertical({
        join_input,
        Container::Horizontal({connect_join_btn, cancel_join_btn}),
    });
    auto direct_modal_comp = Container::Vertical({
        host_input, port_input,
        Container::Horizontal({do_direct_btn, cancel_direct_btn}),
    });

    // Tab 0=main, 1=invite, 2=join, 3=direct, 4=safety, 5=group-create, 6=file-send
    auto root_comp = Container::Tab({
        main_comp,
        invite_modal_comp,
        join_modal_comp,
        direct_modal_comp,
        safety_modal_comp,
        group_modal_comp,
        file_modal_comp,
    }, &active_tab);

    // ── Master renderer ────────────────────────────────────────────────────────
    auto ui = Renderer(root_comp, [&]() -> Element {

        // Snapshot shared state.
        std::vector<cloak::app::ChatApplication::MessageEntry> msgs_snap;
        std::vector<cloak::app::ChatApplication::PeerInfo>     peers_snap;
        std::vector<cloak::app::ChatApplication::GroupEntry>   groups_snap;
        std::string sys_snap;
        std::string invite_snap;
        {
            std::lock_guard lock(state_mutex);
            msgs_snap   = messages;
            peers_snap  = peers;
            groups_snap = groups;
            sys_snap    = status_line;
            invite_snap = invite_code_str;
        }

        // ── Status bar ────────────────────────────────────────────────────────
        const std::string fp_short = app_.my_fingerprint().substr(0, 12) + "...";
        const std::string group_indicator =
            app_.has_active_group() ? " ▣ " + app_.active_group_name() + " " : "";
        auto status_bar = hbox({
            text(" " + app_.my_name() + " ") | bold | color(Color::Black) | bgcolor(Color::Blue),
            text(" FP: " + fp_short + " ") | color(Color::GrayLight),
            separator(),
            text(" " + std::to_string(peers_snap.size()) + " peer(s) ") | color(Color::Cyan),
            separator(),
            group_indicator.empty()
                ? text("") | size(WIDTH, EQUAL, 0)
                : hbox({
                    text(group_indicator) | color(Color::Magenta),
                    separator(),
                  }),
            text(" " + sys_snap + " ") | color(Color::Green) | flex,
            text(" Cloak 0.4 ") | color(Color::GrayDark),
        });

        // ── Left panel ────────────────────────────────────────────────────────
        const uint16_t    listen_port = app_.my_listen_port();
        const std::string my_addr     = app_.my_lan_ip() + ":" +
            (listen_port ? std::to_string(listen_port) : "...");

        Elements left_elems;
        left_elems.push_back(text(" Peers ") | bold | color(Color::Yellow));
        left_elems.push_back(separator());
        left_elems.push_back(search_btn->Render());
        left_elems.push_back(invite_btn->Render());
        left_elems.push_back(join_btn->Render());
        left_elems.push_back(direct_btn->Render());
        left_elems.push_back(safety_btn->Render());
        left_elems.push_back(send_file_open_btn->Render());
        left_elems.push_back(separator());

        if (peer_entries.empty()) {
            left_elems.push_back(text(" No peers found ") | color(Color::GrayDark) | italic);
            left_elems.push_back(text(" Use Search or  ") | color(Color::GrayDark));
            left_elems.push_back(text(" Invite Code    ") | color(Color::GrayDark));
        } else {
            left_elems.push_back(text(" Select peer: ") | color(Color::GrayLight));
            left_elems.push_back(peer_menu->Render() | flex);
        }

        // ── Groups section ────────────────────────────────────────────────────
        left_elems.push_back(separator());
        left_elems.push_back(text(" Groups ") | bold | color(Color::Magenta));
        left_elems.push_back(create_group_btn->Render());
        if (app_.has_active_group()) {
            left_elems.push_back(invite_group_btn->Render());
            left_elems.push_back(leave_group_btn->Render());
        }
        if (!group_entries.empty()) {
            left_elems.push_back(text(" Select group: ") | color(Color::GrayLight));
            left_elems.push_back(group_menu->Render());
        } else {
            left_elems.push_back(text(" No groups yet ") | color(Color::GrayDark) | italic);
        }

        left_elems.push_back(separator());
        left_elems.push_back(text(" Your address: ") | color(Color::GrayDark));
        left_elems.push_back(text(" " + my_addr + " ") | bold | color(Color::Yellow));
        left_elems.push_back(copy_addr_btn->Render());

        auto left_panel = vbox(left_elems) | border | size(WIDTH, EQUAL, 29);

        // ── Message area ──────────────────────────────────────────────────────
        Elements msg_elems;
        if (msgs_snap.empty()) {
            msg_elems.push_back(text("  No messages yet.") | color(Color::GrayDark));
            msg_elems.push_back(
                text("  Connect to a peer and start typing.") | color(Color::GrayDark));
        } else {
            for (const auto& m : msgs_snap) {
                if (m.is_mine) {
                    msg_elems.push_back(hbox({
                        filler(),
                        text(" " + m.sender + ": " + m.text + " ")
                            | color(Color::Cyan) | bgcolor(Color::NavyBlue),
                    }));
                } else {
                    msg_elems.push_back(hbox({
                        text(" " + m.sender + ": " + m.text + " ") | color(Color::White),
                        filler(),
                    }));
                }
            }
        }

        // Show group hint in input area when group is active.
        const bool   has_group = app_.has_active_group();
        const std::string group_hint = has_group
            ? " [Group: " + app_.active_group_name() + "] "
            : "";

        auto right_panel = vbox({
            vbox(msg_elems) | flex | frame,
            separator(),
            has_group
                ? text(group_hint) | color(Color::Magenta) | italic
                : text(""),
            hbox({
                msg_input->Render() | flex,
                send_btn->Render(),
                has_group ? group_send_btn->Render() : text(""),
            }),
        }) | flex | border;

        // ── Base layout ───────────────────────────────────────────────────────
        auto main_doc = vbox({
            status_bar,
            hbox({left_panel, right_panel}) | flex,
        });

        // ── Invite modal overlay ───────────────────────────────────────────────
        if (show_invite_modal) {
            auto modal_doc = vbox({
                text(" ✉ Invite Code ") | bold | center | color(Color::Yellow),
                separator(),
                text("Share this code with your peer:") | color(Color::GrayLight),
                separator(),
                paragraph(invite_snap) | color(Color::Green) | bold | center,
                separator(),
                invite_generating
                    ? (text("  Waiting for peer to connect...") | color(Color::GrayDark))
                    : (text("  Listening — peer can now join.") | color(Color::GrayDark)),
                separator(),
                hbox({
                    copy_code_btn->Render(),
                    text("  "),
                    close_invite_btn->Render(),
                }) | center,
            }) | border | size(WIDTH, EQUAL, 64) | center | clear_under;
            return dbox({main_doc | dim, modal_doc});
        }

        // ── Join modal overlay ─────────────────────────────────────────────────
        if (show_join_modal) {
            auto modal_doc = vbox({
                text(" ↪ Join via Invite Code ") | bold | center | color(Color::Yellow),
                separator(),
                text("Type or paste the code from your peer:") | color(Color::GrayLight),
                separator(),
                join_input->Render() | border,
                separator(),
                hbox({
                    connect_join_btn->Render(),
                    text("  "),
                    cancel_join_btn->Render(),
                }) | center,
                separator(),
                text("  Tip: Ctrl+V to paste  |  Press Connect or Enter")
                    | color(Color::GrayDark) | center,
            }) | border | size(WIDTH, EQUAL, 64) | center | clear_under;
            return dbox({main_doc | dim, modal_doc});
        }

        // ── Direct connect modal overlay ───────────────────────────────────────
        if (show_direct_modal) {
            auto modal_doc = vbox({
                text(" ➡ Direct Connect ") | bold | center | color(Color::Yellow),
                separator(),
                text("Enter the address shown in their bottom-left panel:")
                    | color(Color::GrayLight),
                separator(),
                text(" Host / IP:") | color(Color::GrayLight),
                host_input->Render() | border,
                text(" Port:") | color(Color::GrayLight),
                port_input->Render() | border,
                separator(),
                hbox({
                    do_direct_btn->Render(),
                    text("  "),
                    cancel_direct_btn->Render(),
                }) | center,
                separator(),
                text("  Tip: type or Ctrl+V to paste  |  Tab to switch fields")
                    | color(Color::GrayDark) | center,
            }) | border | size(WIDTH, EQUAL, 58) | center | clear_under;
            return dbox({main_doc | dim, modal_doc});
        }

        // ── Safety number modal overlay ────────────────────────────────────────
        if (show_safety_modal) {
            const std::string peer_name =
                (!peers_snap.empty() && peer_selected < static_cast<int>(peers_snap.size()))
                    ? peers_snap[peer_selected].name : "current peer";
            auto modal_doc = vbox({
                text(" ⚿ Safety Number ") | bold | center | color(Color::Yellow),
                separator(),
                text("Compare this number with " + peer_name + " out-of-band.")
                    | color(Color::GrayLight) | center,
                text("If it matches, you're talking to the right person.")
                    | color(Color::GrayLight) | center,
                separator(),
                text(safety_line1) | bold | color(Color::Green) | center,
                text(safety_line2) | bold | color(Color::Green) | center,
                separator(),
                text("Verify via phone call, in person, or a separate secure channel.")
                    | color(Color::GrayDark) | center,
                separator(),
                hbox({
                    verify_peer_btn->Render(),
                    text("   "),
                    close_safety_btn->Render(),
                }) | center,
                separator(),
                text("  Mark Verified = you confirmed the number matches")
                    | color(Color::GrayDark) | center,
            }) | border | size(WIDTH, EQUAL, 66) | center | clear_under;
            return dbox({main_doc | dim, modal_doc});
        }

        // ── Create group modal overlay ─────────────────────────────────────────
        if (show_group_modal) {
            auto modal_doc = vbox({
                text(" [+] Create Group ") | bold | center | color(Color::Magenta),
                separator(),
                text("Choose a name for your new encrypted group:") | color(Color::GrayLight),
                separator(),
                group_name_input_comp->Render() | border,
                separator(),
                hbox({
                    create_group_confirm_btn->Render(),
                    text("   "),
                    cancel_group_btn->Render(),
                }) | center,
                separator(),
                text("  After creating, select a peer and click Invite to Group")
                    | color(Color::GrayDark) | center,
                text("  Then use Group Msg to send encrypted messages to all members")
                    | color(Color::GrayDark) | center,
            }) | border | size(WIDTH, EQUAL, 62) | center | clear_under;
            return dbox({main_doc | dim, modal_doc});
        }

        // ── File send modal overlay ────────────────────────────────────────────
        if (show_file_modal) {
            auto modal_doc = vbox({
                text(" [▶] Send File ") | bold | center | color(Color::Yellow),
                separator(),
                text("Enter the full path to the file to send:") | color(Color::GrayLight),
                separator(),
                file_path_input_comp->Render() | border,
                separator(),
                hbox({
                    do_send_file_btn->Render(),
                    text("   "),
                    cancel_file_btn->Render(),
                }) | center,
                separator(),
                text("  Supported: jpg/png/gif/mp4/mp3/pdf/txt/zip and more")
                    | color(Color::GrayDark) | center,
                text("  Received files are saved to your Downloads folder")
                    | color(Color::GrayDark) | center,
                text("  Tip: Ctrl+V to paste a path  |  Press Enter or Send File")
                    | color(Color::GrayDark) | center,
            }) | border | size(WIDTH, EQUAL, 66) | center | clear_under;
            return dbox({main_doc | dim, modal_doc});
        }

        return main_doc;
    });

    // ── Global key bindings ────────────────────────────────────────────────────
    auto with_keys = CatchEvent(ui, [&](Event e) -> bool {
        if (e == Event::Escape) {
            if (show_invite_modal)  { show_invite_modal  = false; active_tab = 0; return true; }
            if (show_join_modal)    { show_join_modal    = false; active_tab = 0; return true; }
            if (show_direct_modal)  { show_direct_modal  = false; active_tab = 0; return true; }
            if (show_safety_modal)  { show_safety_modal  = false; active_tab = 0; return true; }
            if (show_group_modal)   { show_group_modal   = false; active_tab = 0; return true; }
            if (show_file_modal)    { show_file_modal    = false; active_tab = 0; return true; }
        }
        if (e == Event::Character('\x11')) { // Ctrl+Q
            screen.ExitLoopClosure()();
            return true;
        }
        return false;
    });

    screen.Loop(with_keys);
    return {};
}

} // namespace cloak::ui
