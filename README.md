# Witness thumbnails

A quick Python script to generate Witness-compatible savefile-sized images.

Images are randomly generated but seeded by their content, which means their generation is consistent

The script needs the Karmina Bold font to be available (in `fonts/Karmina Bold.otf`) but this is not a freely licensed font. Alternatives can be provided.

## Usage

```sh
$ python image.py archipelago.example:12345 PlayerName
```