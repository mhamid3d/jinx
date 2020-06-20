import subprocess
import os

IMG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "img"))
ICON_PATHS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "icon_paths.py"))
QRC_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "jinxicon.qrc"))
RCC_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "jinxicon_rcc.py"))

# This section for updating the variables list
img_list = []

for img in os.listdir(IMG_PATH):
    img_name = os.path.splitext(img)[0]
    img_list.append((img, '{} = ":/jinxicon/img/{}"'.format(img_name, img)))
img_list.sort(key=lambda i: i[0])

# write qrc file
qrc_file = open(QRC_FILE, "w")
qrc_file.write("<RCC>\n")
qrc_file.write('  <qresource prefix="jinxicon">\n')
for qrc_obj in img_list:
    qrc_string = "    <file>img/{}</file>\n".format(qrc_obj[0])
    qrc_file.write(qrc_string)
qrc_file.write("  </qresource>\n")
qrc_file.write("</RCC>\n")
qrc_file.close()

# write rcc file
subprocess.call('pyside2-rcc {} -o {}'.format(QRC_FILE, RCC_FILE), shell=True)
rcc_file = open(RCC_FILE, "rt")
rcc_text = rcc_file.readlines()
rcc_file.close()
rcc_file = open(RCC_FILE, "w")
for line in rcc_text:
    rcc_file.write(line.replace("from PySide2", "from qtpy"))
rcc_file.close()

# write icon_paths file
ip_file = open(ICON_PATHS_FILE, "w")
ip_file.write("from jinxicon import jinxicon_rcc"+'\n'+'\n'+'\n')
for var in img_list:
    ip_file.write(var[1]+'\n')

ip_file.close()