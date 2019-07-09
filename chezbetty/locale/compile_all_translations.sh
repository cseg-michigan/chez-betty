for dir in `find . -mindepth 1 -maxdepth 1 -type d`; do
	pushd $dir/LC_MESSAGES
	msgfmt betty.po
	popd
done

