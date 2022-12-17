from __future__ import annotations
from typing import Optional
import threading
import time

class VimOverleafInstance:
	def __init__(self, buffer_number: int, browser_executable: Optional[str]=None, userdata_dir: Optional[str]=None, driver_path: Optional[str]=None, updatetime: Optional[float]=None)->None:
		if browser_executable is None:
			import vim  # type: ignore
			browser_executable=vim.vars["vim_overleaf_browser_executable"].decode('u8')
		if userdata_dir is None:
			import vim  # type: ignore
			userdata_dir      =vim.vars["vim_overleaf_userdata_dir"].decode('u8')
		if driver_path is None:
			import vim  # type: ignore
			driver_path       =vim.vars["vim_overleaf_driver_path"].decode('u8')
		if updatetime is None:
			import vim  # type: ignore
			updatetime        =float(vim.vars["vim_overleaf_updatetime"])

		self.buffer_number=buffer_number
		self.browser_executable=browser_executable
		self.userdata_dir=userdata_dir
		self.driver_path=driver_path
		self.updatetime=updatetime

		self.thread: Optional[threading.Thread]=None
		self.last_text: Optional[str]=None
		self.connected: bool=False
		self.lock=threading.RLock()  # used to protect `connected` and `thread` etc. since it might be accessed from multiple threads

	def open_browser(self)->None:
		from selenium.webdriver.chrome.options import Options  # type: ignore
		options = Options()
		options.add_argument("user-data-dir=" + self.userdata_dir)
		options.add_argument("disable-popup-blocking")
		options.add_experimental_option("excludeSwitches", ["enable-automation"])  # https://stackoverflow.com/a/57384517/5267751
		options.add_experimental_option("useAutomationExtension", False)

		from selenium.webdriver import Chrome  # type: ignore
		self.driver=Chrome(options=options, executable_path=self.driver_path)
		self.driver.get(self.get_initial_url())

	@property
	def buffer(self):
		return vim.buffers[self.buffer_number]

	def get_initial_url(self)->str:
		text=self.get_vim_text()
		import re
		match_=re.search('overleaf-project-url: (.*?)$', text, re.MULTILINE)
		if not match_:
			return "https://overleaf.com/login"
		return match_[1]

	def on_timer_callback(self)->None:
		"""
		this is run for every timer tick, after it finishes then the text in vim buffer and in the browser should be equal
		unless something unexpected happens.
		"""
		if self.last_text is None:
			self.last_text=self.get_browser_text()
			__=self.edit_vim_text(self.get_vim_text(), self.last_text)
			return
		vim_text=self.get_vim_text()
		browser_text=self.get_browser_text()
		new_text, conflict=self.three_way_merge(self.last_text, vim_text, browser_text)
		if not self.edit_browser_text(browser_text, new_text): return
		if not self.edit_vim_text(vim_text, new_text): return
		self.last_text=new_text

	@staticmethod
	def three_way_merge(last_text: str, vim_text: str, browser_text: str)->tuple[str, bool]:
		"""
		prioritize browser_text in case of conflict

		return (resulting text, conflict?)
		second return value is true iff there's conflict
		"""
		from merge3 import Merge3  # type: ignore
		result: list[str]=[]
		conflict: bool=False
		for tag, *rest in Merge3(last_text, vim_text, browser_text).merge_groups():
			if tag=="conflict":
				conflict=True
				last_part, vim_part, browser_part=rest
				result.append(browser_part)
			else:
				assert tag in ("unchanged", "a", "b", "same")
				part,=rest
				result.append(part)
		return "".join(result), conflict

	def run_watcher(self)->None:
		from selenium.common.exceptions import WebDriverException  # type: ignore
		while True:
			with self.lock:
				if not self.connected:
					self.thread=None
					return
				try:
					self.on_timer_callback()
				except WebDriverException as e:  # e.g. the browser is closed by the user
					import traceback
					print("Overleaf client error:")
					traceback.print_exc(file=sys.stdout)
					self.disconnect()
					self.thread=None
					return
			time.sleep(self.updatetime)

	def get_browser_text(self)->str:
		return self.driver.execute_script((#JavaScript
			r"""
			{
				let editor=_ide.outlineManager.shareJsDoc.cm6.view
				return editor.state.doc.toString()
			}
			"""))

	def get_vim_text(self)->str:
		import vim  # type: ignore
		return '\n'.join(self.buffer)

	def edit_browser_text(self, old: str, new: str)->bool:
		"""
		return whether the edit is successful. It might not be successful if for example
		the text in the browser has been edited/different from old
		"""
		if old==new: return True
		import difflib

		changes=[]
		for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new).get_opcodes():
			if tag=="equal": continue
			assert tag in ("insert", "replace", "delete")
			changes.append({"from": i1, "to": i2, "insert": new[j1:j2]})

		return self.driver.execute_script((#JavaScript
		r"""
		{
			let editor=_ide.outlineManager.shareJsDoc.cm6.view
			if(editor.state.doc.toString()!=arguments[0]) return false
			editor.dispatch({ changes: arguments[1] })
			return true
		}
		"""), old, changes)  # double check just in case

	def edit_vim_text(self, old: str, new: str)->bool:
		"""
		return whether the edit is successful.
		"""
		if old==new: return True
		import vim  # type: ignore
		self.buffer[:]=new.split("\n")
		return True

	def connect(self)->None:
		self.last_text=None
		with self.lock:
			assert not self.connected, "already connected"
			self.connected=True
			if self.thread is None:
				self.thread=threading.Thread(target=self.run_watcher)
				assert self.thread is not None
				self.thread.start()
		print("Connected.")

	def disconnect(self)->None:
		with self.lock:
			assert self.connected, "not connected"
			self.connected=False
		print("Disconnected.")

	def quit(self)->None:
		self.driver.quit()

	def recompile(self)->None:
		"""
		equivalent to clicking the "recompile" button in the browser
		"""
		return self.driver.execute_script((#JavaScript
			r"""
			document.querySelector(".btn-recompile[aria-label=Recompile]:not(.dropdown-toggle)").click()
			"""))

	@staticmethod
	def current_buffer_number()->int:
		import vim  # type: ignore
		return vim.current.buffer.number
		
	objects: dict[int, VimOverleafInstance]={}  # buffer number → object

	@staticmethod
	def object_for_current_buffer()->VimOverleafInstance:
		return VimOverleafInstance.objects[VimOverleafInstance.current_buffer_number()]

def VimOverleafOpenBrowser()->None:
	buffer_number=VimOverleafInstance.current_buffer_number()
	if buffer_number in VimOverleafInstance.objects:
		VimOverleafInstance.objects[buffer_number].quit()
	VimOverleafInstance.objects[buffer_number]=VimOverleafInstance(buffer_number)
	VimOverleafInstance.objects[buffer_number].open_browser()

def VimOverleafConnect()->None:
	VimOverleafInstance.object_for_current_buffer().connect()

def VimOverleafDisconnect()->None:
	VimOverleafInstance.object_for_current_buffer().disconnect()

def VimOverleafRecompile()->None:
	VimOverleafInstance.object_for_current_buffer().recompile()
