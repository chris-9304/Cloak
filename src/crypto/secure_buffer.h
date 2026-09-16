#pragma once

#include <array>
#include <cstddef>
#include <cstring>
#include <vector>

#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#else
#include <sys/mman.h>
#endif

namespace cloak::crypto {

namespace detail {

inline void lock_pages(void* p, size_t n) {
#if defined(_WIN32)
    VirtualLock(p, n);
#else
    mlock(p, n);
#endif
}

inline void unlock_pages(void* p, size_t n) {
#if defined(_WIN32)
    VirtualUnlock(p, n);
#else
    munlock(p, n);
#endif
}

// Volatile byte-wise zero: not optimized away, unlike memset/std::fill.
inline void secure_zero(void* p, size_t n) {
#if defined(_WIN32)
    SecureZeroMemory(p, n);
#else
    volatile uint8_t* vp = static_cast<volatile uint8_t*>(p);
    while (n--) *vp++ = 0;
#endif
}

} // namespace detail

// Owning, fixed-size buffer for secret key material.
// - Page-locked on construction (best-effort: VirtualLock on Windows, mlock on POSIX).
// - Securely zeroed on destruction.
// - Move-only: never copied, never logged, never serialized unencrypted.
template <size_t N>
class SecureBuffer {
public:
    SecureBuffer() {
        detail::lock_pages(buf_.data(), N);
    }

    ~SecureBuffer() {
        detail::secure_zero(buf_.data(), N);
        detail::unlock_pages(buf_.data(), N);
    }

    // Move-only.
    SecureBuffer(SecureBuffer&& o) noexcept : buf_(o.buf_) {
        detail::secure_zero(o.buf_.data(), N);
    }
    SecureBuffer& operator=(SecureBuffer&& o) noexcept {
        if (this != &o) {
            detail::secure_zero(buf_.data(), N);
            buf_ = o.buf_;
            detail::secure_zero(o.buf_.data(), N);
        }
        return *this;
    }
    SecureBuffer(const SecureBuffer&)            = delete;
    SecureBuffer& operator=(const SecureBuffer&) = delete;

    uint8_t*       data() noexcept       { return buf_.data(); }
    const uint8_t* data() const noexcept { return buf_.data(); }
    static constexpr size_t size() noexcept { return N; }

    uint8_t&       operator[](size_t i)       { return buf_[i]; }
    const uint8_t& operator[](size_t i) const { return buf_[i]; }

    auto begin()       { return buf_.begin(); }
    auto end()         { return buf_.end(); }
    auto begin() const { return buf_.begin(); }
    auto end()   const { return buf_.end(); }

private:
    std::array<uint8_t, N> buf_{};
};

} // namespace cloak::crypto
