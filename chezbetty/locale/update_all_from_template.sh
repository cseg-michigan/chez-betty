for dir in `find . -mindepth 1 -maxdepth 1 -type d`; do
	msgmerge --backup=none --update $dir/LC_MESSAGES/betty.po betty.pot
done

