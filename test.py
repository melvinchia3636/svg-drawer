#library import
from turtle import Screen, Turtle, Vec2D
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
from selenium.webdriver.common.alert import Alert
from bs4 import BeautifulSoup

#screen setup
screen = Screen()
screen.setup()
screen.screensize(8000, 8000)
turtle = Turtle()
turtle.speed(1000000)
turtle.width(2)

#cubic bezier fomula
b = lambda t: p0*(1-t)**2 * (1-t) + 3*p1*(1-t)**2*t + 3*p2*(1-t)*t**2 + p3*t**2 * t

options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options, executable_path='\\'.join(os.getcwd().split('\\')[:-3])+'\\chromedriver.exe')
soup = BeautifulSoup(open('\\'.join(os.getcwd().split('\\')[:-2])+'\\Symphony Of The Seas\\IDP-DECK18.svg', 'r').read(), 'lxml')

for item in soup.findAll(['path', 'polyline', 'rect', 'polygon', 'line']):
  #draw path
  if item.name == 'path':
    #convert relative path into absolute
    converter = open('converter.html', 'r').read()
    open('converter.html', 'w').write(re.sub(r"'(.+)'", "'"+item['d'].replace('z', '')+"'", converter))
    driver.get('file:///C:/Users/kelvi/Documents/Python_V2/cruise%20ship%20data/deck%20plan/Quantum%20Of%20The%20Seas/svg drawer/converter.html')
    data = driver.find_element_by_tag_name('body').text
    # building data structure
    data = [i.strip() for i in re.split('(M|C|L|S|H|V)', data)[1:]]
    data = [data[i:i+2] for i in range(0, len(data), 2)]
    for i in range(len(data)):
      if data[i][0] == 'M':
        data[i][1] = [[float(i) for i in data[i][1].split(',')]]
      #cubic bezier curve [[float, float], [float, float], [float, float]]
      elif data[i][0] == 'C':
        data[i][1] = [sum([[float(l) for l in [j[0]]+['-'+k for k in j[1:]] if l] for j in i], []) for i in [[[k for k in j.split('-') ] for j in i.strip().split(',')] for i in data[i][1].split('C') if i]][0]
        data[i][1] = [data[i][1][j:j+2] for j in range(0, len(data[i][1]), 2)]
      #straight line [[float, float]]
      elif data[i][0] == 'L':
        data[i][1] = [sum([[float(l) for l in [j[0]]+['-'+k for k in j[1:]] if l] for j in i], []) for i in [[[k for k in j.split('-') ] for j in i.strip().split(',')] for i in data[i][1].split('L') if i]]
      #continued bezier curve [[float, float], [float, float]]
      elif data[i][0] == 'S':
        data[i][1] = [sum([[float(l) for l in [j[0]]+['-'+k for k in j[1:]] if l] for j in i], []) for i in [[[k for k in j.split('-') ] for j in i.strip().split(',')] for i in data[i][1].split('S') if i]][0]
        data[i][1] = [data[i][1][j:j+2] for j in range(0, len(data[i][1]), 2)]
      #vertical line
      elif data[i][0] == 'V':
        data[i][1] = [[data[i-1][1][-1][0], float(data[i][1])]]
      #horizontal line
      elif data[i][0] == 'H':
        data[i][1] = [[float(data[i][1]), data[i-1][1][-1][1]]]
    #start the drawing iteration
    turtle.width(float(item['stroke-width'])*8 if 'stroke-width' in item.attrs else 2)
    turtle.color(item['stroke'] if 'stroke' in item.attrs else 'black')
    turtle.fillcolor(item['fill']) if 'fill' in item.attrs and item['fill'] != 'none' else ''
    if 'fill' in item.attrs and item['fill'] != 'none':
      turtle.begin_fill()
    for i in range(len(data)):
      if data[i][0] == 'M':
        turtle.penup()
        turtle.goto(data[i][1][0])
      #cubic bezier curve
      if data[i][0] == 'C':
        p0 = Vec2D(*data[i-1][1][-1])
        p1 = Vec2D(*data[i][1][0])
        p2 = Vec2D(*data[i][1][1])
        p3 = Vec2D(*data[i][1][2])
        turtle.penup()
        turtle.goto(p0)
        turtle.pendown()
        t = 0
        while t <= 1:
            position = b(t)
            turtle.setheading(turtle.towards(position))
            turtle.goto(position)
            t += 0.1
            print(position)
      #continued cubic bezier curve
      elif data[i][0] == 'S':
        p0 = Vec2D(*origin if i==0 else data[i-1][1][-1])
        p1 = Vec2D(2*data[i-1][1][-1][0]-data[i-1][1][-2][0], 2*data[i-1][1][-1][1]-data[i-1][1][-2][1])
        p2 = Vec2D(*data[i][1][0])
        p3 = Vec2D(*data[i][1][1])
        turtle.penup()
        turtle.goto(p0)
        turtle.pendown()
        t = 0
        while t <= 1:
            position = b(t)
            turtle.setheading(turtle.towards(position))
            turtle.goto(position)
            t += 0.1
            

      #straight line
      elif data[i][0] in 'LVH':
        turtle.pendown()
        turtle.goto(*data[i][1][0])
    if 'fill' in item.attrs and item['fill'] != 'none':
      turtle.end_fill()

  #draw polyline
  elif item.name == 'polyline':
    points = [[float(j) for j in i.split(',')] for i in item['points'].split() if i]
    turtle.width(float(item['stroke-width'])*5 if 'stroke-width' in item.attrs else 1)
    turtle.penup()
    for i in points:
      turtle.setheading(turtle.towards(*i))
      turtle.goto(*i)
      turtle.pendown()
  #draw rectangle
  elif item.name == 'rect':
    x, y, width, height, color  = float(item['x']), float(item['y']), float(item['width']), float(item['height']), item['fill']
    turtle.setheading(0)
    turtle.penup()
    turtle.pencolor('black')
    turtle.fillcolor(color) if color != 'none' else ''
    turtle.begin_fill()
    turtle.goto(x, y)
    turtle.pendown()
    turtle.width(0.5)
    for i in range(2):
      turtle.forward(width)
      turtle.left(90)
      turtle.forward(height)
      turtle.left(90)
    turtle.end_fill()
  #draw polygon
  if item.name == 'polygon':
    points, color, width = [[float(j) for j in i.strip().split(',')] for i in item['points'].split()], item['fill'] if 'fill' in item.attrs else 'white', float(item['stroke-width'])*5 if 'stroke-width' in item.attrs else 1
    turtle.penup()
    turtle.setheading(turtle.towards(*points[0]))
    turtle.goto(*points[0])
    turtle.pencolor('black')
    turtle.width(width)
    turtle.fillcolor(color if color != 'none' else 'white')
    turtle.begin_fill()
    turtle.pendown()
    for i in points[1:]:
      turtle.setheading(turtle.towards(*i))
      turtle.goto(*i)
    turtle.end_fill()
  #draw line
  if item.name == 'line':
    p1, p2 = [float(item['x1']), float(item['y1'])], [float(item['x2']), float(item['y2'])]
    print(p1, p2)
    color = item['stroke']
    turtle.color(color if color and color != 'none' else 'black')
    turtle.penup()
    turtle.goto(*p1)
    turtle.pendown()
    turtle.goto(*p2)


driver.close()
driver.quit()
screen.mainloop()
