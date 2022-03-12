import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
from selenium.webdriver.common.alert import Alert
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from turtle import Vec2D
import numpy as np
import matplotlib.path as mpath
import matplotlib.patches as mpatches
import math
from adjustText import adjust_text
from mpl_interaction import figure_pz

class SvgOnMatplotlib(object):
	def __init__(self, fig, ax, svg, driver_path=None):
		self.fig = fig
		self.ax = ax
		self.options = Options()
		self.options.add_argument('--headless')
		self.driver = webdriver.Chrome(options=self.options)
		self.soup = BeautifulSoup(open(svg, 'r').read(), 'lxml')
		self.min_x, self.min_y, self.win_width, self.win_height = list(map(float, self.soup.find('svg')['viewbox'].split()))
		self.real_width, self.real_height =  [float(self.soup.find('svg')['width'].replace('pt', '') if 'width' in self.soup.find('svg').attrs else 1000), 
											  float(self.soup.find('svg')['height'].replace('pt', '')  if 'height' in self.soup.find('svg').attrs else 1000)]
		self.txt_lst = []
		self.clip_path = {}
		self.setup_plot()

	def setup_plot(self):
		self.fig.canvas.mpl_connect('scroll_event', self.change_text_size)
		self.ax.set_ylim(self.min_x, self.min_x+self.win_width)
		self.ax.set_xlim(self.min_y, self.min_y+self.win_height)
		self.ax.axes.xaxis.set_visible(False)
		self.ax.axes.yaxis.set_visible(False)

	def change_text_size(self, e):
		if e.button == 'up':
			for i in self.txt_lst:
				i.set_fontsize(i.get_fontsize()*1.05)
		if e.button == 'down':
			for i in self.txt_lst:
				i.set_fontsize(i.get_fontsize()/1.05)

	def deltaTransformPoint(self, matrix, point):
		dx = point['x'] * matrix['a'] + point['y'] * matrix['c'] + 0
		dy = point['x'] * matrix['b'] + point['y'] * matrix['d'] + 0
		return { 'x': dx, 'y': dy }

	def decomposeMatrix(self, matrix) :
		px = self.deltaTransformPoint(matrix, { 'x': 0, 'y': 1 })
		py = self.deltaTransformPoint(matrix, { 'x': 1, 'y': 0 })

		skewX = ((180 / math.pi) * math.atan2(px['y'], px['x']) - 90)
		skewY = ((180 / math.pi) * math.atan2(py['y'], py['x']))
		return {
			'translateX': matrix['e'],
			'translateY': matrix['f'],
			'scaleX': math.sqrt(matrix['a'] * matrix['a'] + matrix['b'] * matrix['b']),
			'scaleY': math.sqrt(matrix['c'] * matrix['c'] + matrix['d'] * matrix['d']),
			'skewX': skewX,
			'skewY': skewY,
			'rotation': skewX}

	def get_absolute_path(self, path):
		converter = open('converter.html', 'r').read()
		open('converter.html', 'w').write(re.sub(r"'(.+)'", "'"+re.sub(r'(\d)\s(\d)', r'\1,\2' , path.replace('\n', '')).replace('z', '')+"'", converter))
		self.driver.get('file:///'+os.getcwd()+'/converter.html')
		data = self.driver.find_element_by_tag_name('body').text
		return data

	def get_bevier_curve(self, p0, p1, p2, p3):
		#cubic bezier fomula
		b = lambda t: p0*(1-t)**2 * (1-t) + 3*p1*(1-t)**2*t + 3*p2*(1-t)*t**2 + p3*t**2 * t
		return [b(i) for i in np.arange(0.0, 1.1, 0.1)]

	def build_path(self, path):
		data = self.get_absolute_path(path)
		data = [i.strip() for i in re.split('(M|C|L|S|H|V|Q)', re.sub(r'\d(\s)\d', ',', data))[1:]]
		data = [data[i:i+2] for i in range(0, len(data), 2)]
		print(data)

		for i in range(len(data)):

			#starting point [[float, float]]
			if data[i][0] == 'M':
				data[i][1] = [[float(i) for i in data[i][1].split(',')]]
			
			#cubic bezier curve [[float, float], [float, float], [float, float]]
			elif data[i][0] == 'C':
				data[i][1] = [float(i.strip()) for i in data[i][1].split(',')]
				data[i][1] = [data[i][1][j:j+2] for j in range(0, 6, 2)]
			
			#straight line [[float, float]]
			elif data[i][0] == 'L':
				data[i][1] = [sum([[float(l) for l in [j[0]]+['-'+k for k in j[1:]] if l] for j in i], []) for i in [[[k for k in j.split('-') ] for j in i.strip().split(',')] for i in data[i][1].split('L') if i]]
			
			#continued bezier curve [[float, float], [float, float]]
			elif data[i][0] == 'S':
				data[i][1] = [sum([[float(l) for l in [j[0]]+['-'+k for k in j[1:]] if l] for j in i], []) for i in [[[k for k in j.split('-') ] for j in i.strip().split(',')] for i in data[i][1].split('S') if i]][0]
				data[i][1] = [data[i][1][j:j+2] for j in range(0, len(data[i][1]), 2)]
			
			#vertical line [[float, float], [float, float]]
			elif data[i][0] == 'V':
				data[i][1] = [[data[i-1][1][-1][0], float(data[i][1])]]
			
			#horizontal line [[float, float], [float, float]]
			elif data[i][0] == 'H':
				data[i][1] = [[float(data[i][1]), data[i-1][1][-1][1]]]
		return data

	def get_clip(self, item):
		item = item.find(['path', 'polyline', 'rect', 'polygon', 'line', 'text'])
		if item.name == 'path':
			patch = self.Path(item)

		elif item.name == 'rect':
			x, y, width, height = float(item['x']), float(item['y']), float(item['width']), float(item['height'])
			node = [(x, y), (x+width, y), (x+width, y+height), (x, y+height), (x, y)]
			node = [tuple(reversed(i)) for i in node]
			patch = mpatches.PathPatch(mpath.Path(node), facecolor=(0, 0, 0, 0))

		elif item.name == 'polygon':
			patch = self.Polygon(item)

		return patch


	def Path(self, item):
		code = []
		node = []
		color = item['stroke'] if 'stroke' in item.attrs else None
		width = item['stroke-width'].replace('px', '') if 'stroke-width' in item.attrs else 1
		fill = item['fill'] if 'fill' in item.attrs else 'alpha' if 'fill' in item.attrs and item['fill'] == 'none' else 'black'
		if 'style' in item.attrs:
			style = item['style']
			if 'fill' in style: fill = re.search(r'fill:(.*?);', style).group(1)
			if 'stroke' in style: color = re.search(r'stroke:(.*?);', style).group(1)
			if 'stroke-width' in style: width = re.search(r'width:(.*?);', style).group(1).replace('px', '')

		data = self.build_path(item['d'])
		for i in range(len(data)):
			if data[i][0] == 'M':
				current = data[i][1][0]
				node.append(current)
				code.append(mpath.Path.MOVETO)

			if data[i][0] == 'C':
				p0 = Vec2D(*data[i-1][1][-1])
				p1 = Vec2D(*data[i][1][0])
				p2 = Vec2D(*data[i][1][1])
				p3 = Vec2D(*data[i][1][2])
				points = self.get_bevier_curve(p0, p1, p2, p3)
				node += points
				code += [mpath.Path.LINETO]*len(points)

			if data[i][0] == 'S':
				p0 = Vec2D(*data[i-1][1][-1])
				p1 = Vec2D(2*data[i-1][1][-1][0]-data[i-1][1][-2][0], 2*data[i-1][1][-1][1]-data[i-1][1][-2][1])
				p2 = Vec2D(*data[i][1][0])
				p3 = Vec2D(*data[i][1][1])
				points = self.get_bevier_curve(p0, p1, p2, p3)
				node += points
				code += [mpath.Path.LINETO]*len(points)

			if data[i][0] in 'LHV':
				node.append(data[i][1][0])
				code.append(mpath.Path.LINETO)
		node = [tuple(reversed(i)) for i in node]
		path = mpath.Path(node, code)
		patch = mpatches.PathPatch(path, facecolor=(0, 0, 0, 0) if fill == 'alpha' else fill, ec=color if color else (0, 0, 0, 0), lw=float(width))
		if 'clip-path' in item.attrs:
			current_clip = item['clip-path']
			if 'url' in current_clip:
				current_clip = self.clip_path[re.search(r'url\(#(.*?)\)', current_clip).group(1)]
				area_to_clip = self.get_clip(current_clip)
				self.ax.add_patch(area_to_clip)
				patch.set_clip_path(area_to_clip)
		return patch

	def Polyline(self, item):
		color = item['stroke'] if 'stroke' in item.attrs else None
		width = item['stroke-width'] if 'stroke-width' in item.attrs else 1
		fill = item['fill'] if 'fill' in item.attrs and item['fill'] != 'none' else None
		node = [[float(j) for j in i.split(',')] for i in item['points'].split() if i]
		code = [mpath.Path.MOVETO]+[mpath.Path.LINETO]*(len(node)-1)
		node = [tuple(reversed(i)) for i in node]
		path = mpath.Path(node, code)
		patch = mpatches.PathPatch(path, facecolor=fill if fill else (0, 0, 0, 0), ec=color if color else (0, 0, 0, 0), lw=float(width))

		return patch

	def Rect(self, item):
		x, y, width, height = float(item['x']), float(item['y']), float(item['width']), float(item['height'])
		stroke_width = item['stroke-width'] if 'stroke-width' in item.attrs else 1
		color = item['stroke'] if 'stroke' in item.attrs else None
		fill = item['fill'] if 'fill' in item.attrs and item['fill'] != 'none' else None
		alpha = 1
		if 'style' in item.attrs:
			style = item['style']
			if 'fill' in style: fill = re.search(r'fill:(.*?);', style).group(1)
			if 'stroke' in style: color = re.search(r'stroke:(.*?);', style).group(1)
			if 'stroke-width' in style: stroke_width = int(re.search(r'width:(.*?);', style).group(1).replace('px', ''))
			if re.match(r'(;|^)opacity:(.*?)(;|$)', style): alpha = float(re.search(r'(;|^)opacity:(.*?)(;|$)', style).group(2))
		code = [mpath.Path.MOVETO]+[mpath.Path.LINETO]*4
		node = [(x, y), (x+width, y), (x+width, y+height), (x, y+height), (x, y)]
		node = [tuple(reversed(i)) for i in node]
		path = mpath.Path(node, code)
		patch = mpatches.PathPatch(path, facecolor=fill if fill else (0, 0, 0, 0), ec=color if color else (0, 0, 0, 0), lw=float(stroke_width), alpha=alpha)

		return patch

	def Polygon(self, item):
		color = item['stroke'] if 'stroke' in item.attrs else None
		width = item['stroke-width'] if 'stroke-width' in item.attrs else 1
		fill = item['fill'] if 'fill' in item.attrs and item['fill'] != 'none' else None
		node = [[float(j) for j in i.split(',')] for i in item['points'].split() if i]
		node += [node[0]]
		node = [tuple(reversed(i)) for i in node]
		code = [mpath.Path.MOVETO]+[mpath.Path.LINETO]*(len(node)-1)
		path = mpath.Path(node, code)
		patch = mpatches.PathPatch(path, facecolor=fill if fill else (0, 0, 0, 0), ec=color if color else (0, 0, 0, 0), lw=float(width))

		return patch

	def Line(self, item):
		p1, p2 = [float(item['x1']), float(item['x2'])], [float(item['y1']), float(item['y2'])]
		color = item['stroke'] if 'stroke' in item.attrs else None
		width = item['stroke-width'] if 'stroke-width' in item.attrs else 1

		return p1, p2, color, width

	def Text(self, item):
		x, y = [float(item['x']) if 'x' in item.attrs else 0, float(item['y']) if 'y' in item.attrs else 0]
		transform = item['transform'] if 'transform' in item.attrs else None
		text = item.text.strip()
		font_size = float(item['font-size']) if 'font-size' in item else 1.0
		if transform:
			if 'matrix' in transform:
				matrix = self.decomposeMatrix(dict(zip('abcdef', list(map(float, re.search(r'matrix\((.+)\)', transform).group(1).split())))))
				x, y = matrix['translateX'], matrix['translateY']
		else:
			matrix = {}

		return x, y, text, font_size, matrix

	def draw(self):
		if self.soup.findAll('clippath'):
			for i in self.soup.findAll('clippath'):
				self.clip_path[i['id']] = i
		for item in self.soup.findAll(['path', 'polyline', 'rect', 'polygon', 'line', 'text']):
			try:
				if item.name == 'path':
					patch = self.Path(item)
					self.ax.add_patch(patch)
					plt.pause(0.001)

				elif item.name == 'polyline':
					patch = self.Polyline(item)
					self.ax.add_patch(patch)
					plt.pause(0.001)

				elif item.name == 'rect':
					patch = self.Rect(item)
					self.ax.add_patch(patch)
					plt.pause(0.001)

				elif item.name == 'polygon':
					patch = self.Polygon(item)
					self.ax.add_patch(patch)
					plt.pause(0.001)

				elif item.name == 'line':
					p1, p2, color, width = self.Line(item)
					self.ax.plot(p2, p1, color=color if color else (0, 0, 0, 0), lw=float(width))
					plt.pause(0.001)

				elif item.name == 'text':
					x, y, text, font_size, matrix = self.Text(item)
					self.txt_lst.append(self.ax.text(y, x, text, rotation=360-matrix['rotation']+90.0 if matrix else 0, fontsize=2, ha='right', va=('top' if matrix['rotation']+90.0 in [0, 180] else 'bottom') if matrix else 'top'))
					plt.pause(0.001)
			except: pass

			print(item.name)

if __name__ == "__main__":
	'''fig = figure_pz(figsize=(19, 17), dpi=100)
				fig.tight_layout()
				driver = '\\'.join(os.getcwd().split('\\')[:-3])+'\\chromedriver.exe'
				ax = fig.add_subplot()
				svg = 'C:/Users/kelvi/Documents/quantum.svg'
				SvgOnMatplotlib(fig, ax, svg, driver_path=driver).draw()'''

	fig = figure_pz(figsize=(15, 15), dpi=100)
	fig.tight_layout()
	'''
	count = 1

	for i in list(range(14, 15)):
		exec('ax'+str(count)+' = fig.add_subplot(1, 1, count)')
		exec('ax'+str(count)+'.axes.xaxis.set_visible(False)')
		exec('ax'+str(count)+'.axes.yaxis.set_visible(False)')
		count += 1

	count = 1

	for i in list(range(14, 15)):
		svg = '\\'.join(os.getcwd().split('\\')[:-2])+'\\Quantum Of The Seas\\IDP-DECK{}.svg'.format(str(i).zfill(2))
		exec('SvgOnMatplotlib(fig, ax'+str(count)+', svg, driver_path=driver).draw()')
		count += 1
	'''
	svg = 'IDP-DECK14.svg'
	ax= fig.add_subplot(1, 1, 1)
	ax.axes.xaxis.set_visible(False)
	ax.axes.yaxis.set_visible(False)
	SvgOnMatplotlib(fig, ax, svg).draw()
	plt.show()
	os.system('TASKKILL /F /IM chrome.exe')