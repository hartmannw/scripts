# In order for navigate.py to work. The following should be added to your .bashrc/.bash_alias file.

## .bashrc
export LUMANN_DATA=/PATH/TO/DIR # directory where data will be stored

## .bash_alias
navigate() {
    dir=$(pwd)
    output="$(navigate.py -c $dir $@)"
    if [ $? != 0 ]; then
        if [ -n "$output" ]; then
            printf "${output}\n"
        fi
    elif [[ -d "${output}" ]]; then
        cd "${output}" && navigate.py -a $(pwd)
    else
        printf "navigate '$@' not found\n "
        printf "\n${output}\n\n"
        printf "Try --help for more information\n"
    fi
}

alias n=navigate
