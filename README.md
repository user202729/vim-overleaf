# vim-overleaf
Edit Overleaf document from vim, with synchronization features.

## Disclaimer

Backup your data. This script was quickly written in a few hours, there's no guarantee.

There are some other features, but undocumented features may change later. (documented features may also change)

## Installation

Install `merge3` Python library.

Install the plugin as usual.

You need to download Google Chrome browser and the `chromedriver` executable.

## Usage

* Open any file.
* Execute `:OverleafOpenBrowser`.
* Navigate to an Overleaf project.
* Execute `:OverleafConnect`. At this point if the text in the browser and the editor are not equal then
the editor text will be overwritten with the browser text, nevertheless using the undo feature in Vim suffices.
* Commands `:OverleafDisconnect` and `:OverleafRecompile` are available.

You may want to make your own key bindings.

If in the file there's a line with content such as
```tex
% overleaf-project-url: https://overleaf.com/project/abcdef
```
then that URL will be opened in the browser when `:OverleafOpenBrowser` is executed.

## Configuration

Set the following global variables in `.vimrc` as usual.

If they're not set, they will be set to some reasonable default value once the plugin is loaded.

* `g:vim_overleaf_userdata_dir`: directory to the userdata directory. Will contain Chrome profile.
* `g:vim_overleaf_driver_path`: path to the `chromedriver` file.
* `g:vim_overleaf_updatetime`: time for check update, in seconds.

## Internal implementation note

I tried `three_merge` library as well but...
```
from three_merge import merge
merge("zzzz", "bcde", "bcd")
```
results in an infinite loop.
