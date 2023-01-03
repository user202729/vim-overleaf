vim9script noclear

if exists("g:vim_overleaf_loaded")
  finish
else
  g:vim_overleaf_loaded = 1
endif

def SetDefault(name: string, value: string)
	if !has_key(g:, name)
		g:[name] = value
	endif
enddef

SetDefault("vim_overleaf_browser_executable", "")  # TODO doesn't really work
SetDefault("vim_overleaf_userdata_dir", "/tmp/.vim-overleaf-userdata")
SetDefault("vim_overleaf_driver_path", "chromedriver")
SetDefault("vim_overleaf_updatetime", "2")

command! OverleafReloadPython :call OverleafReloadPython()
command! OverleafOpenBrowser  :py3 VimOverleafOpenBrowser()
command! OverleafConnect      :py3 VimOverleafConnect()
command! OverleafDisconnect   :py3 VimOverleafDisconnect()
command! OverleafRecompile    :py3 VimOverleafRecompile()

# (copied from Mundo)
const plugin_path = escape(expand('<sfile>:p:h'), '\')

def SyncContent(timer: number)
	py3 VimOverleafInternalSyncContent()
enddef

if type(g:vim_overleaf_updatetime) == v:t_string
	g:vim_overleaf_updatetime = str2float(g:vim_overleaf_updatetime)
endif
const updatetime_ms = float2nr(round(g:vim_overleaf_updatetime * 1000))
if updatetime_ms == 0
	echoerr "updatetime cannot be zero!"
	finish
endif
timer_start(updatetime_ms, SyncContent, {"repeat": -1})



def g:OverleafReloadPython()
	exec 'py3file ' .. plugin_path .. '/VimOverleaf.py'
enddef
g:OverleafReloadPython()

