function(cloak_target_warnings tgt)
    if(MSVC)
        target_compile_options(${tgt} PRIVATE
            /W4
            /WX
            /permissive-
            /Zc:__cplusplus
            /Zc:preprocessor
        )
    else()
        target_compile_options(${tgt} PRIVATE
            -Wall
            -Wextra
            -Werror
        )
    endif()
endfunction()
