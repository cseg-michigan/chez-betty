Language Support
================

This is intended as a quick-ref for how to do common things. If you
add a new string, you have to update a few translation databases. For
more complete information, the pylons i18n docs are here:
http://docs.pylonsproject.org/docs/pyramid/en/latest/narr/i18n.html

**Make sure you are in the betty virtualenv before doing anything**

See the top-level README for instructions on getting set up.

Common Operations
-----------------

Pretty much all the interesting stuff lives in `chezbetty/locale`

### Add a new language

```bash
cd /chez-betty/chezbetty/locale
# Replace 'es' (spanish) with your language code:
mkdir -p es/LC_MESSAGES
msginit -l es -o es/LC_MESSAGES/betty.po
```

When the translation is complete and ready to go live, edit
`chezbetty/templates/index.jinja2` and add the new language to
the footer.

### Add or Update a source string

You must first regenerate the global template.
```bash
cd /chez-betty
pybabel extract -F babel.cfg -o chezbetty/locale/betty.pot chezbetty
```

Then you have to update the translation template for each language.
There is a helper script that will do this for you:
```bash
cd /chez-betty/chezbetty/locale
./update_all_from_template.sh
```

Next the actual translations for each language need to be added. This requires
editing the language-specific .po files.

I strongly advise installing [poedit](https://poedit.net/), but this is just
technically just a text file, so any editor will do
```bash
poedit es/LC_MESSAGES/betty.po
```

Finally, the translations have to be compiled. Again, there's a helper script:
```bash
cd /chez-betty/chezbetty/locale
./compile_all_translations.sh
```

### Langauge support in a fresh checkout

The translations must be compiled:

```bash
cd /chez-betty/chezbetty/locale
./compile_all_translations.sh
```
