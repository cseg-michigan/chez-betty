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
pot-create -c lingua.config -o chezbetty/locale/betty.pot chezbetty
```

Then you have to update the translation template for each language.
```bash
cd /chez-betty/chezbetty/locale
# Replace 'es' (spanish) with your language code:
msgmerge --update es/LC_MESSAGES/betty.po betty.pot
```

Next the actual translations for each language need to be added. This requires
editing the language-specific .po files.
```bash
vi/poedit/other_editor es/LC_MESSAGES/betty.po
```

Finally, the translations have to be compiled.
```bash
cd /chez-betty/chezbetty/locale
# foreach language
  pushd es/LC_MESSAGES
  msgfmt betty.po
  popd
```

### Langauge support in a fresh checkout

The translations must be compiled. An outstanding **TODO** is to add
this to an automated deploy script.

```bash
cd /chez-betty/chezbetty/locale
# foreach language
  pushd es/LC_MESSAGES
  msgfmt betty.po
  popd
```
