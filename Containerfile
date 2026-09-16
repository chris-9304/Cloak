# Builds and runs cloak-relay (the internet relay server) in a Linux container via
# Podman or OrbStack/Docker. Only the relay server + the libraries it depends on
# (core/crypto/wire/transport/session/store/transfer/group) are built here -- there is
# no terminal UI client on this image (see README.md's "Build & Run on macOS/Linux"
# section for the native build, which is what you'd use for the desktop client anyway
# now that it's being replaced by a Rust server + Android app per project notes).
#
# Uses the project's own debug-posix/release-posix CMake presets (added for the
# macOS/Linux portability pass), which already handle everything except vcpkg itself.

FROM debian:bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ninja-build \
    pkg-config \
    autoconf \
    automake \
    autoconf-archive \
    libtool \
    git \
    curl \
    zip \
    unzip \
    tar \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Full clone (not --depth 1): vcpkg.json pins a specific historical baseline commit
# that a shallow clone won't contain.
RUN git clone https://github.com/microsoft/vcpkg /opt/vcpkg \
    && /opt/vcpkg/bootstrap-vcpkg.sh -disableMetrics
ENV VCPKG_ROOT=/opt/vcpkg

WORKDIR /build
COPY CMakeLists.txt CMakePresets.json vcpkg.json vcpkg-configuration.json ./
COPY cmake ./cmake
COPY include ./include
COPY src ./src
COPY tests ./tests

# First run downloads and builds all vcpkg dependencies from source (15-30 min);
# cached by Docker layer caching on subsequent builds as long as the files above
# don't change.
RUN cmake --preset release-posix
RUN cmake --build --preset release-posix --target cloak-relay

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/build/release-posix/src/relay/cloak-relay /usr/local/bin/cloak-relay

EXPOSE 8765
ENTRYPOINT ["/usr/local/bin/cloak-relay"]
CMD ["--port", "8765"]
