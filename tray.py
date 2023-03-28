import serial
import serial.tools.list_ports
import mysql.connector
import sounddevice as sd
import soundfile as sf
import tkinter as tk
import wx
import wx.adv
import configparser
from tkinter import filedialog as fd
from tkinter import ttk
from tkinter import messagebox
from datetime import datetime

soundname = 'sound.wav' # имя звукового файла для воспроизведения

# Функция для сворачивания окна в трей
def minimize_to_tray():
    root.withdraw() # Скрываем окно программы
    icon.visible = True # Показываем иконку в трее

# Функция для восстановления окна из трея
def restore_from_tray():
    root.deiconify() # Показываем окно программы
    icon.visible = False # Скрываем иконку в трее

# Создаем класс TaskBarIcon для работы с системным треем с помощью wx.TaskBarIcon
class TaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self):
        super(TaskBarIcon, self).__init__() # Вызываем конструктор родительского класса
        self.set_icon("icon_off.png") # Устанавливаем начальную иконку
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down) # Привязываем обработчик левого клика мыши на иконке

    def set_icon(self, path): # Метод для установки новой иконки по пути к файлу
        icon = wx.Icon(path) # Создаем объект wx.Icon из файла
        self.SetIcon(icon) # Устанавливаем новую иконку

    def on_left_down(self, event): # Метод-обработчик левого клика мыши на иконке
        restore_from_tray() # Восстанавливаем окно программы из трея


#Создаем функцию для сохранения настроек в файл
def save_settings():
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        # 'server_name': server_name.get(),
        # 'database_name': database_name.get(),
        # 'table_name': table_name.get(),
        # 'user_name': user_name.get(),
        # 'password': password.get(),
        'port_name': port_var.get(),
        'file_name': file_name.get(),
        'baudrate': baudrate_var.get()
    }
    with open('settings.ini', 'w') as f:
        config.write(f)

#Создаем функцию для загрузки настроек из файла
def load_settings():
    try:
        config = configparser.ConfigParser()
        config.read('settings.ini')
        # server_name.delete(0, END)
        # server_name.insert(0, config['DEFAULT']['server_name'])
        # database_name.delete(0, END)
        # database_name.insert(0, config['DEFAULT']['database_name'])
        # table_name.delete(0, END)
        # table_name.insert(0, config['DEFAULT']['table_name'])
        # user_name.delete(0, END)
        # user_name.insert(0, config['DEFAULT']['user_name'])
        # password.delete(0, END)
        # password.insert(0, config['DEFAULT']['password'])
        port_var.set (config['DEFAULT']['port_name'])
        baudrate_var.set (int(config['DEFAULT']['baudrate']))
        file_name.set(config['DEFAULT']['file_name'])
    except FileNotFoundError:
        pass

# Создаем функцию для получения списка доступных портов
def get_ports():
    # Используем функцию list_ports.comports() из модуля pySerial
    ports = serial.tools.list_ports.comports()
    # Возвращаем список имен портов
    return [port.device for port in ports]

def open_port():
    global serial_port
    # Получаем значение из выпадающего списка портов
    port = port_var.get()
    # Получаем значение из поля ввода скорости передачи данных (бод)
    baudrate = int(baudrate_var.get())
    # Открываем порт с выбранными параметрами и сохраняем его как глобальную переменную
    try:
        serial_port = serial.Serial(port, baudrate)
    except serial.SerialException:
        # Если порт недоступен, выводим сообщение об ошибке и завершаем программу с помощью exit
        print("Ошибка открытия порта")
        exit()

# Создаем функцию для выбора файла из диалога
def  select_file():
    # Отображаем диалог выбора файла и получаем имя выбранного файла
    file_name = fd.askopenfilename()
    if file_name: # если файл был выбран
        entry.delete(0, tk.END) # очищаем текстовое поле
        entry.insert(0, file_name) # вставляем имя файла в текстовое поле

# Функция для запуска и остановки чтения данных из порта
def toggle_read():
    global reading  # Используем глобальную переменную для хранения состояния чтения
    if reading:  # Если чтение включено, то выключаем его и меняем текст кнопки и иконку в трее
        reading = False
        start_button.config(text="Запустить")
        icon.set_icon("icon_off.png")
        if serial_port.is_open:
            serial_port.close()
    else:  # Если чтение выключено, то включаем его и меняем текст кнопки и иконку в трее
        reading = True
        start_button.config(text="Остановить")
        icon.set_icon("icon_on.png")
        try:
            serial_port
        except NameError:
            open_port()
        if not serial_port.is_open:
            serial_port.open()

# Создаем функцию для чтения и записи данных из порта в базу данных
def read_and_write():
    if reading:  # Если чтение включено, то читаем данные из порта и записываем их в базу данных
        data = serial_port.readline()  # Читаем строку данных из порта
        data = data.decode('utf-8').strip()  # Декодируем данные из байтов в строку и убираем пробелы и переносы строк

        # Добавляем данные в виджет Text с новой строки
        text.insert('end', data + '\n')
        # Прокручиваем текст до конца
        text.see('end')

        # Проверяем, что пользователь выбрал файл
        file_name = entry.get()
        if file_name:
            # Открываем файл для записи в режиме дозаписи ('a')
            with open(file_name, 'a') as f:
                # Записываем данные о вставке в файл
                f.write(data+"\n")
                # Закрываем файл
                f.close()
        else:
            messagebox.showinfo("Ошибка","Выберите файл")
            toggle_read()

        # Разделение строки на значения
        data = data.split(',')

        # Извлекаем температуру и влажность из данных
        Time = data[0]
        Humidity = data[1]
        Pressure = data[2]
        Alt = data[3]
        AirTemp = data[4]
        WaterTemp = data[5]
        Salinity = data[6]

        #print(data)  # Выводим данные на экран для отладки
        print(datetime.utcfromtimestamp(int(data[0])).strftime('%m-%d %H:%M:%S'),data[1],data[2],data[3],data[4],data[5],data[6])

        if float(WaterTemp) == -127:
            # если есть, воспроизводим звуковой файл
            data_aud, fs = sf.read(soundname)
            sd.play(data_aud, fs)
            sd.wait()
            WaterTemp = 25.03
            Salinity = int( float(Salinity) * ( 1.0 + 0.02 * ( -127.0 - 25.0)))


        # Вставка значений в таблицу Meteo

        sql = "INSERT INTO Meteo (Time,Humidity,Pressure,Alt,AirTemp,WaterTemp,Salinity)  VALUES (FROM_UNIXTIME(%s), %s, %s, %s, %s, %s, %s)"
        val = (Time,Humidity,Pressure,Alt,AirTemp, WaterTemp,Salinity)
        try:
            cursor.execute(sql, val)
            sql_conn.commit()  # Подтверждаем изменения в базе данных
        except mysql.connector.Error as err:
            messagebox.showinfo("Ошибка", format(err))

    # Запускаем функцию снова через 1 секунду (строку не перемещать)
    root.after(1000, read_and_write)


# Создаем переменную для хранения состояния чтения данных из порта (True - включено, False - выключено)
reading = False

# Создаем объект приложения wx.App (необходимо для работы с системным треем)
app = wx.App()

# Создаем объект TaskBarIcon
icon = TaskBarIcon()

# Создаем окно программы с помощью tkinter.Tk()
root = tk.Tk()
root.title("Программа для чтения данных из порта")
#root.geometry("800x400")

frame1 = ttk.Frame(root)
frame1.pack(fill=tk.BOTH, expand=True)

frame2 = ttk.Frame(root)
frame2.pack(fill=tk.BOTH, expand=True)

# Создаем метку с текстом "Port"
port_label = tk.Label(frame1, text="Port", width=10)
port_label.grid(row=0, column=0)

# Создаем переменную для хранения выбранного значения из списка портов
port_var = tk.StringVar(frame1)

# Получаем список доступных портов
port_list = get_ports()

# Если список не пустой, то устанавливаем первый элемент как значение по умолчанию
if port_list:
    port_var.set(port_list[0])

# Создаем выпадающий список с доступными портами
port_menu = tk.OptionMenu(frame1, port_var, *port_list)
port_menu.grid(row=0, column=1)

# Создаем метку с текстом "Baudrate"
baudrate_label = tk.Label(frame1, text="Baudrate", width=10)
baudrate_label.grid(row=0, column=2)

# Создаем переменную для хранения выбранного значения из списка скоростей
baudrate_var = tk.StringVar(root)

# Создаем список возможных скоростей порта
baudrate_list = ["300", "600", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]

# Устанавливаем значение по умолчанию 9600
baudrate_var.set("9600")

# Создаем выпадающий список с доступными скоростями
baudrate_menu = tk.OptionMenu(frame1, baudrate_var, *baudrate_list)
baudrate_menu.grid(row=0,column=3)

# Создаем переменную для хранения имени файла
file_name = tk.StringVar(root)

load_settings()


entry = tk.Entry(frame2,width=60) # создаем виджет Entry для ввода имени файла
entry.insert(0, file_name.get())
entry.grid(row=1,column=0) # размещаем виджет в окне


# Создаем кнопку для запуска функции выбора файла
btn2 = tk.Button (frame2, text="...", command=select_file, width=2)
btn2.grid(row=1, column=1 ,sticky="ns")

# Создаем виджет Text для отображения данных из порта
text = tk.Text(frame2,width=45)
text.grid(row=2, column=0 )

# Создаем виджет Scrollbar для прокрутки текста
scrollbar = tk.Scrollbar(frame2, command=text.yview)
scrollbar.grid(row=2, column=1 ,sticky="ns")

# Связываем виджеты Text и Scrollbar друг с другом
text.config(yscrollcommand=scrollbar.set)


# Создаем кнопку для запуска и остановки чтения данных из порта с помощью tkinter.Button
start_button = tk.Button(frame2, text="Запустить", command=toggle_read)
start_button.grid(row=3, column=0)

# Создаем кнопку для сохранения настроек
save_button = tk.Button(frame2, text="Save settings", command=save_settings)
save_button.grid(row=3, column=1)


# Привязываем обработчик сворачивания окна программы к событию Unmap
root.bind("<Unmap>", lambda event: minimize_to_tray())


# Подключаемся к базе данных MySQL с помощью mysql.connector.connect
try:
    sql_conn = mysql.connector.connect(host='localhost', user='root', password='', database='Hydra')
except mysql.connector.Error as err:
    messagebox.showinfo("Ошибка", format(err))
else:
    cursor = sql_conn.cursor()


# Запускаем функцию для чтения и записи данных из порта в базу данных
read_and_write()


# Запускаем главный цикл обработки событий окна программы
root.mainloop()
