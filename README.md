# WhatsApp Chat Browser

**WhatsApp Chat Browser** is a tool to render your archived WhatsApp chats.
WhatsApp allows exporting your chats as ZIP files for archival purposes.
**WhatsApp Chat Browser** reads these ZIP files, turns them into HTML web
pages, and serves them to your browser for viewing or printing.

# Usage

1. Start **WhatsApp Chat Browser**.
2. Load a chat archive using `Open` from the File menu, or just drag
   and drop the archive file into the application.
3. Start the built-in Web server using `Start` from the `Server` menu.
4. Click on `Open URL in Browser` from the `Server` menu. This opens
   a new browser window showing your chat history.

See below for more details.

# Installation

On Windows, you can download and run the `wacb.exe` executable.

On any platform, first install (Python)[https://python.org].
Then you can either download the Wacb Wheel, or you can install
**WhatsApp Chat Browser** from the Python Package Index by
running `pip install wacb` in a console. Afterwards, you can
run `wacb` or `python -m wacb`.

# Details

**WhatsApp Chat Browser** reads chat histories from ZIP files exported
by WhatsApp. The process is documented
[here](https://faq.whatsapp.com/1180414079177245/).

After loading a chat history into **WhatsApp Chat Browser**, the GUI
will show the word **Loaded** in green. You can now set a title for
this chat, to be used as the HTML title field, and you can also select
your name from the `My Name` drop-down. This chooses which messages
are shown on the right-hand side.

Then, you can click `Start` in the `Server` menu to start the
built-in Web server. The status will now show **Running** in green,
and the status bar will show the URL that you can now open in your
Web browser. For convenience, you can also use `Copy URL to Clipboard`
or `Open URL in Browser` from the `Server` menu.

# The Menu

- `File`
  - `Open ...` Opens a chat history. Typically, these are ZIP files,
    although you can also open a `_chat.txt` file. If you choose
    multiple files, they will be merged. You can also use `Ctrl-o`.
  - `Merge ...` Merges a chat history with the one that is already
    open. You can also choose multiple files at once to merge them
    all into the same timeline.
  - `Close` Does the obvious. You can also use `Ctrl-w`.
  - `Export`
    - `Chat` Exports the chat history as a ZIP file including the
      chat messages as a `_chat.txt` file, along with all attachments.
      This becomes useful after merging multiple chats into one.
    - `HTML` Exports the chat history as a ZIP file containing HTML
      files (starting with `index.html`), including all attachments.
  - `Exit` Does the obvious. You can also use `Ctrl-x`.
- `Filter`
  - `By date ...` Filters the chat history by start and end dates.
    This can be done after loading the chat history, but before starting
    the Web server.
  - `Reset` Resets the date filter.
- `Server`
  - `Start` Starts the built-in Web server.
  - `Stop` Stops the built-in Web server.
  - `Copy URL to Clipboard` Copy the URL to the clipboard. You can then
    paste the URL into your favorite browser's address bar.
  - `Open URL in Browser` Starts your default browser, or opens a new
    tab in your default browser, and opens your chat history.

# Options

The `Options` menu has the following options. Note that the `Options`
menu is disabled when the built-in Web server is running.

- `Autostart` Automatically start the built-in Web server immediately
  after loading a chat archive.
- `HTML` Options related to the HTML rendering.
  - `Inline Images` If activated, images are shown in the chat.
    If deactivated, only links to images are shown.
  - `Inline Video` Same as `Inline Images`, but for videos.
  - `Inline Audio` Same as `Inline Images`, but for audio files.
  - `View As` either
    - `Single Page` Show all chat messages on a single Web page.
    - `Annual Pages` Use one Web page for each year.
    - `Monthly Pages` Use one web page for each month.
  - `Style Sheet`
    - `Built-In` Use the built-in style sheet for formatting.
    - `Load ...` Use a separate CSS file for formatting messages.
    - `Save Template As ...` Save the built-in style sheet to a file
      for editing.
  - `Emojis`
    - `Images` If activated, render emojis using images from an emoji library.
      If deactivated, let your browser render them.
    - `Inline` If activated, include emoji image data in the HTML code.
      If deactivated, include image links instead.
    - `Ignore Ascii` If activated, when using an emoji library, ignore
      plain-Ascii images within the emoji library (e.g,. an emoji for
      the `#` sign).
    - `Select Images ...` Select an emoji library.
    - `Download Images ...` Download the _official_ emoji library from
      [Unicode](https://www.unicode.org/emoji/charts/)
- `HTTP`
  - `Configure` Configure the host name and port number to use for the
    built-in Web server. Using `localhost` as the host name is highly
    recommended. Using your actual host name might make the built-in
    Web server visible from your local network -- use at your own risk.
    When the port number to `0`, the built-in Web server automatically
    chooses an available port number. When set to any other valid
    port number (between 1024 and 65535), the built-in Web server
    binds to the same address every time.

# Missing Details

There are a lot of details that WhatsApp does _not_ include in its
exported chat histories:

- Reactions to messages (i.e., likes, hearts, etc.).
- References to qoted messages. You will see the reply, but no link
  to the message that was quoted.
- Image captions. You will see the image, but not the text that was
  in the same message as the image.

Because this information is not exported, **WhatsApp Chat Browser**
can not reconstruct it.

Also note that WhatsApp uses participant names from your phone's
address book. For participants that are not in your address book,
you may see an alias starting with `~` or simply a phone number.

# Formatting

Formatting of the chat history is controlled by a CSS Stylesheet.
**WhatsApp Chat Browser** by default uses a built-in stylesheet.
If you want to modify formatting, you can save the built-in stylesheet
using `Save Template As ...` from the `Options` menu, edit it, and
then use `Load ...` to use your modified style sheet instead.

# Emojis

Emojis are complicated. For example, there is an emoji `U+1f3c3`
called "Runner". However, this emoji can then be combined with a
skin tone value, with a female or male indicator, with a direction,
etc. You can end up with a sequence like
`U+1f3c3` (Runner), `U+1f3ff` (Emoji modifier fitzpatrick type-6),
`U+200d' (Zero-width joiner), `U+2642` (Male sign), `U+fe0f`
(Emoji variation selector), `U+200d' (Zero-width joiner again),
`U+27a1` (black rightwards arrow), `U+fe0f`
(Emoji variation selector again) to choose the emoji of a male
runner with dark skin color running towards the right. So while
you choose a single emoji on your phone's keyboard, it ends up
as a comples series of Unicode code points.

The easiest thing to do is to let your browser handle this mess.
This is done if `Images` from the `Emojis` option is _disabled_.
However, your browser might not have the prettiest emojis, and
some browsers might be confused by more complex sequences. E.g.,
for the above sequence, some browsers might show the runner, male
sign and arrow separately.

Therefore, it is possible to let **WhatsApp Chat Browser** replace
these emoji sequences with images from an emoji library, which you
have to download separately. Two options are supported out of the
box:

- The [noto-emoji](https://github.com/googlefonts/noto-emoji) package.
  Download its latest release package as a ZIP file, and then use
  `Select Images` from the `Emojis` option to use this set of images.
  The noto-emoji package contains multiple sets of the same emojis.
  Use the drop-down list to select one of them.
- The _official_ [Unicode emojis](https://www.unicode.org/emoji/charts/),
  comprised of the
  [Full Emoji List](https://www.unicode.org/emoji/charts/full-emoji-list.html) and,
  optionally, the
  [Full Emoji Modifiers](https://www.unicode.org/emoji/charts/full-emoji-modifiers.html) list.
  Use `Download Images` from the `Emojis` option to download one or
  both HTML pages and to extract the emojis. Note that these pages are
  huge, and the Unicode Web server might be slow, so the download can
  take 10 minutes or more.

**WhatsApp Chat Browser** will scan an emoji library and discover its
codepoint sequences for which images are available. It will then replace
any of these codepoint sequences that occur in your messages with the
matching picture from the library. It will then ignore any _modifiers_
or combining marks at the tail of the codepoint sequence. E.g., if the
emoji library includes an image for `U+1f3c3` (Runner) _only_, then
**WhatsApp Chat Browser** will use the Runner image and drop the
subsequent modifiers, such as the skin tone and the male/female sign.

This allows you to tailor an emoji library of your own, if you like.

The noto-emoji library also includes images for some plain Ascii
characters, such as the number sign `#`. This might result in some
unpleasant side effects. That's what the `Ignore Ascii` option is
for.

# Configuration

Configuration options are stored in the JSON-formatted configuration
file `~/.wacb`.

**WhatsApp Chat Browser** might misbehave if this file is broken, or
if it references files (like the emoji database or a style sheet) that
do not exist. So if anything goes wrong, try deleting this file. It
will then be re-created from built-in default values.

# Command Line

When installed from the Wheel or using pip, you also get the `wacb-cli`
and `wacb-merge` command-line tools.

`wacb-cli` can be used to convert chat histories to HTML, or to run
the web server from the command line. It also reads the `~/.wacb`
configuration file and therefore applies the same options configured
in the GUI.

`wacb-merge` can be used to merge multiple chat histories into the
same timeline, i.e., the equivalent of loading multiple chat histories
in the GUI and then exporting them as a chat history of its own.

# API

Python developers will find a rich, modular API. Use the source.

# Some Gritty Details

In its exported chat histories, WhatsApp uses localized timestamps
and keywords (e.g., "attached" translated according to your phone's
settings at the time of the export). **WhatsApp Chat Browser** will
probably get confused by chat histories exported using non-western
locales.

Even within the western hemisphere, there is an issue with
localized timestamps, in particular the use of dates formatted as
"day/month/year" in Great Britain versus "month/day/year" in the
US. **WhatsApp Chat Browser** uses the former when it encounters
a british locale. When using dots instead of slashes,
**WhatsApp Chat Browser** uses "day.month.year".

