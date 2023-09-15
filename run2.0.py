#https://pt.scribd.com/read/336522490/10-Inducoes-hipnoticas-para-profissionais# 
import tkinter as tk
from tkinter import ttk
from playwright.sync_api import sync_playwright
from PyPDF2 import PdfMerger
import os
import re
import sys
import time
import shutil
import threading
from datetime import datetime

ZOOM = 0.625

def download_book(book_url, log_widget):

	# create cache dir
	book_filename = book_url.split('/')[5]

	output_folder = f'{os.getcwd()}/{book_filename}'
	os.makedirs(output_folder, exist_ok=True)
	cache_dir = f'{output_folder}/cache'
	os.makedirs(cache_dir, exist_ok=True)

	try:
		os.mkdir(cache_dir)
	except FileExistsError:
		pass

	with sync_playwright() as playwright:
		browser = playwright.chromium.launch(headless=False)
		context = browser.new_context(storage_state="session.json" if 'session.json' in os.listdir('.') else None)

		page = context.new_page()
		page.goto('https://www.scribd.com/login', wait_until='domcontentloaded')

		page.locator("div.user_row").wait_for(state='attached', timeout=0)

		print('Login efetuado com sucesso')

		storage = context.storage_state(path="session.json")
		context.close()
		browser.close()

		browser = playwright.chromium.launch(headless=True)

		print('Carregando visualização...')

		context = browser.new_context(
			storage_state=  "session.json",
			viewport={'width': 1200, 'height': 1600},
			ignore_https_errors = True,
			user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
		)
		context.set_extra_http_headers({'Accept-Language': 'en-US,en;q=0.9'})

		page = context.new_page()
		page.goto(book_url.replace('book', 'read'))

		if 'Browser limit exceeded' in page.content():
			context.close()
			browser.close()
			sys.exit('You have tried to read this from too many computers or web browsers recently, and will need to wait up to 24 hours before returning to this book.')

		# retrieve fonts
		font_style = page.locator('#fontfaces').inner_html()

		# open display menu
		page.locator('.icon-ic_displaysettings').wait_for(state='visible')
		page.evaluate("() => document.querySelector('.icon-ic_displaysettings').click()")

		# change to vertical mode
		page.locator('.vertical_mode_btn').wait_for(state='visible')
		page.evaluate("() => document.querySelector('.vertical_mode_btn').click()")

		# open toc menu
		page.locator('div.vertical_page[data-page="0"]').wait_for(state='visible')
		page.evaluate("() => document.querySelector('.icon-ic_toc_list').click()")
		chapter_selector = page.locator('li.text_btn[role="none"]')
		chapter_selector.nth(0).wait_for(state='visible')

		# retrieve the number of chapters
		num_of_chapters = chapter_selector.count()

		# load the first chapter
		page.evaluate("() => document.querySelector('li.text_btn[data-idx=\"0\"]').click()")
		chapter_no = 1

		# to render the chapter pages and save them as pdf
		render_page = context.new_page()
		render_page.set_viewport_size({"width": 1200, "height": 1600})

		while True:

			page.locator('div.vertical_page[data-page="0"]').wait_for()

			chapter_pages = page.locator('div.vertical_page')
			number_of_chapter_pages = chapter_pages.count()

			# print(f'Downloading chapter {chapter_no}/{num_of_chapters} ({number_of_chapter_pages} pages)')
			print(f'Contruindo a pagina {chapter_no}/{num_of_chapters} ({number_of_chapter_pages} páginas)')

			merger = PdfMerger()

			page_no = 1

			while True:

				page_elem = chapter_pages.nth(page_no-1)
				html = page_elem.inner_html()

				# replace img urls
				html = html.replace('src="/', 'src="https://www.scribd.com/')

				# set page size
				match = re.findall('width: ([0-9.]+)px; height: ([0-9.]+)px;', html)[0]
				width, height = float(match[0]), float(match[1])
				style = f'@page {{ size: {width*ZOOM}px {height*ZOOM}px; margin: 0; }} @media print {{ html, body {{ height: {height*ZOOM}px; width: {width*ZOOM}px;}}}}'
				html = re.sub('data-colindex="0" style="', 'data-colindex="0" x="', html)
				html = re.sub('position: absolute.*?"', f'overflow: hidden; height: {height}px; width: {width}px; white-space: nowrap; zoom: {ZOOM};"', html)

				# render page
				content = f'<style>{style}{font_style}</style>{html}'
				render_page.set_content(content)

				# print pdf
				pdf_file = f'{cache_dir}/{chapter_no}_{page_no}.pdf'
				render_page.pdf(path=pdf_file, prefer_css_page_size = True)
				merger.append(pdf_file)

				if page_no == number_of_chapter_pages:
					merger.write(f"{cache_dir}/{chapter_no}.pdf")
					merger.close()
					break

				page_no += 1

			if chapter_no == num_of_chapters:
				break

			page.evaluate("() => document.querySelectorAll('button.load_next_btn')[0].click()")

			time.sleep(1)
			chapter_no += 1

	print('Juntando paginas...')
	merger = PdfMerger()

	for chapter_no in range(1, num_of_chapters+1):
		merger.append(f"{cache_dir}/{chapter_no}.pdf")

	final_pdf_path = f"{output_folder}/{book_filename}.pdf"
	merger.write(final_pdf_path)

	merger.close()

	# delete cache dir
	shutil.rmtree(cache_dir)
	print(f"Download Concluído com Sucesso!!! \nVocê pode encontrar na pasta deste programa")
	os.startfile(output_folder)

	def save_successful_download():
		file_path = 'download_history.txt'
		current_date = datetime.now().strftime('%Y-%m-%d')
		
		# Verifica se o arquivo existe, se não, cria
		if not os.path.exists(file_path):
			with open(file_path, 'w') as f:
				pass
		
		# Adiciona a data atual ao arquivo de histórico
		with open(file_path, 'a') as f:
			f.write(f"{current_date}\n")

	save_successful_download()

def save_successful_download(book_url):
	current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
	with open('/mnt/data/download_history.txt', 'a') as f:
		f.write(f"[{current_date}] {book_url}\n")

def start_download():
    book_url = url_entry.get()
    thread = threading.Thread(target=download_book, args=(book_url, log_text))
    thread.start()

# GUI Tkinter
root = tk.Tk()
root.title("Downloader de Livros do Scribd")

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

url_label = ttk.Label(frame, text="URL do Livro:")
url_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

url_entry = ttk.Entry(frame, width=50)
url_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

download_button = ttk.Button(frame, text="Iniciar Download", command=start_download)
download_button.grid(row=1, columnspan=2, sticky=tk.W + tk.E, padx=5, pady=5)

log_text = tk.Text(frame, wrap=tk.WORD, width=50, height=15)
log_text.grid(row=2, columnspan=2, sticky=tk.W + tk.E, padx=5, pady=5)

scrollbar = tk.Scrollbar(frame, command=log_text.yview)
scrollbar.grid(row=2, column=2, sticky=tk.N + tk.S)

log_text.config(yscrollcommand=scrollbar.set)

#contanto quantos downloads foram feitos hoje
def count_downloads_today(file_path='download_history.txt'):
    if not os.path.exists(file_path):
        return 0  # Se o arquivo não existe, retorna 0

    current_date = datetime.now().strftime('%Y-%m-%d')
    count = 0

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()  # Remove espaços em branco e quebras de linha
            if line == current_date:
                count += 1  # Incrementa o contador se a data da linha corresponder à data atual

    return count


# Contar os downloads de hoje e atualizar o rótulo de alerta
downloads_today = count_downloads_today('download_history.txt')
alert_text = f"Você fez {downloads_today} download hoje!"

# Adicionando o rótulo de alerta
alert_label = ttk.Label(frame, text=alert_text, foreground="red")
alert_label.grid(row=3, columnspan=2, sticky=tk.W + tk.E, padx=5, pady=5)

scrollbar = tk.Scrollbar(frame, command=log_text.yview)
scrollbar.grid(row=2, column=2, sticky=tk.N + tk.S)

log_text.config(yscrollcommand=scrollbar.set)

class IORedirector(object):
    def __init__(self, text_area):
        self.text_area = text_area

    def write(self, str):
        self.text_area.insert(tk.END, str)
        self.text_area.see(tk.END)

    def flush(self):
        pass

stdout = IORedirector(log_text)
sys.stdout = stdout

root.mainloop()
