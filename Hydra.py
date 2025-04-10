import serial
import serial.tools.list_ports
import mysql.connector
import sounddevice as sd
import soundfile as sf
import tkinter as tk
import wx
import wx.adv
import configparser
import paho.mqtt.client as mqtt
import json
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
        'server_name': server_name.get(),
        'database_name': database_name.get(),
        'table_name': table_name.get(),
        'user_name': user_name.get(),
        'password': password.get(),
        'port_name': port_var.get(),
        'file_name': file_entry.get(),
        'baudrate': baudrate_var.get()
    }
    with open('settings.ini', 'w') as f:
        config.write(f)

#Создаем функцию для загрузки настроек из файла
def load_settings():
    try:
        config = configparser.ConfigParser()
        config.read('settings.ini')
        server_name.set(config['DEFAULT']['server_name'])
        database_name.set(config['DEFAULT']['database_name'])
        table_name.set(config['DEFAULT']['table_name'])
        user_name.set(config['DEFAULT']['user_name'])
        password.set(config['DEFAULT']['password'])
        port_var.set (config['DEFAULT']['port_name'])
        baudrate_var.set (config['DEFAULT']['baudrate'])
        #file_name.set(config['DEFAULT']['file_name'])
        #file_entry.delete(0, END)
        file_entry.insert(0, config['DEFAULT']['file_name'])
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
    except serial.SerialException as err:
        # Если порт недоступен, выводим сообщение об ошибке и завершаем программу с помощью exit
        print(f"Error: {err}")
        print("Ошибка открытия порта")
        errLog.insert('end', "Ошибка открытия порта" + '\n')
        messagebox.showinfo("Ошибка открытия порта")
        exit()

# Настройки MQTT
mqtt_broker = '192.168.5.104'
mqtt_port = 1883
mqtt_topic = 'hydra'

# Аутентификационные данные MQTT
mqtt_username = 'mqtt'
mqtt_password = 'mqtt'

# Функция для обработки входящих сообщений MQTT
def on_message(client, userdata, msg):
    print(f"Received message: {msg.payload}")

# Инициализация MQTT клиента
mqtt_client = mqtt.Client()
#mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
#mqtt_client.on_message = on_message

# Устанавливаем аутентификацию
mqtt_client.username_pw_set(username=mqtt_username, password=mqtt_password)
mqtt_client.connect(mqtt_broker, mqtt_port, 60)
mqtt_client.subscribe(mqtt_topic)

while not mqtt_client.is_connected():
    mqtt_client.loop()
    print(mqtt_client.is_connected())

# Создаем функцию для выбора файла из диалога
def  select_file():
    # Отображаем диалог выбора файла и получаем имя выбранного файла
    file_name = fd.askopenfilename()
    if file_name: # если файл был выбран
        file_entry.delete(0, tk.END) # очищаем текстовое поле
        file_entry.insert(0, file_name) # вставляем имя файла в текстовое поле

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
        except NameError as err:
            print(f"Error: {err}")
            open_port()
        if not serial_port.is_open:
            serial_port.open()

# Создаем функцию для чтения и записи данных из порта в базу данных
def read_and_write():
    if reading:  # Если чтение включено, то читаем данные из порта и записываем их в базу данных
        try:
            while not serial_port.isOpen():
                open_port()
            if serial_port.isOpen():
                serial_port.write(b'Hello')
                data = serial_port.readline()  # Читаем строку данных из порта
            else:
                print ("Port unavailable")
                errLog.insert('end', "Port unavailable" + '\n')

            try:
                data = data.decode('utf-8').strip()  # Декодируем данные из байтов в строку и убираем пробелы и переносы строк
            except UnicodeDecodeError:
                print("Error: Unable to decode byte string.")
                errLog.insert('end', "Error: Unable to decode byte string." + '\n')
                print(data)
                data = "error"
        except serial.SerialException as err:
            data = None
            print(f"Error: {err}")
            #errLog.insert('end', "Serial port error" + err + '\n')
            try:
                serial_port.close()
            except serial.SerialException:
                pass
        if data:
            # Добавляем данные в виджет Text с новой строки
            text.insert('end', data + '\n')
            # Прокручиваем текст до конца
            text.see('end')

            # Проверяем, что пользователь выбрал файл
            file_name = file_entry.get()
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
            if len(data) == 7:

                notValid = "False"
                for x in data:
                    if not x.isdigit():
                        try:
                            float(x)
                        except ValueError:
                            #пришли не валидные данные
                            notValid = "True"
                            data_aud, fs = sf.read(soundname)
                            sd.play(data_aud, fs)
                            sd.wait()

                if notValid == "False":
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

                    if int(Humidity) >= 0 and int(Humidity) <= 100 \
                        and float(AirTemp) >= 10 and float(AirTemp) <= 50 \
                        and float(WaterTemp) >= 10 and float(WaterTemp) <= 50 \
                        and int(Salinity) >= 0 and int(Salinity) <= 3000:

                            # Вставка значений в таблицу Meteo
                            sql = "INSERT INTO Meteo (Time,Humidity,Pressure,Alt,AirTemp,WaterTemp,Salinity)  VALUES (FROM_UNIXTIME(%s), %s, %s, %s, %s, %s, %s)"
                            val = (Time,Humidity,Pressure,Alt,AirTemp, WaterTemp,Salinity)
                            try:
                                cursor.execute(sql, val)
                                sql_conn.commit()  # Подтверждаем изменения в базе данных

                            except mysql.connector.Error as err:
                                messagebox.showinfo("Ошибка SQL", format(err))
                                errLog.insert('end', "Ошибка SQL" + format(err) + '\n')

                            # Создание JSON объекта
                            json_data = json.dumps(data)

                            # Отправка данных в MQTT
                            #mqtt_client.loop()
                            mqtt_client.publish(mqtt_topic, json_data)
                            """
                            if not mqtt_client.is_connected():
                                print("Сервер MQTT недоступен")
                                errLog.insert('end', "Сервер MQTT недоступен" + '\n')
                                try:
                                    mqtt_client.reconnect()
                                except Exception as e:
                                    print(f"Ошибка при попытке восстановления соединения: {e}")
                                    errLog.insert('end', "Ошибка при попытке восстановления соединения:" + format(e) + '\n')
                            else:
                                try:
                                    mqtt_client.publish(mqtt_topic, json_data)
                                except Exception as e:
                                    print(f"Ошибка отправки данных mqtt: {e}")
                                    errLog.insert('end', "Ошибка отправки данных mqtt:" + format(e) + '\n')
                                    """

                    else:
                        messagebox.showinfo("Ошибка Данных")
                        errLog.insert('end', "Ошибка Данных" + '\n')

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
#file_name = tk.StringVar(root)

#Создаем переменные для хранения параметров подключения к базе данных
server_name = tk.StringVar(root)
database_name = tk.StringVar(root)
table_name = tk.StringVar(root)
user_name = tk.StringVar(root)
password = tk.StringVar(root)


file_entry = tk.Entry(frame2,width=60) # создаем виджет Entry для ввода имени файла
#file_entry.insert(0, file_name.get())
file_entry.grid(row=1,column=0) # размещаем виджет в окне

load_settings()

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

# Создаем виджет Text для отображения лога ошибок и прокрутку
errLog = tk.Text(frame2,width=45, height=7)
errLog.grid(row=3, column=0 )
errScroll = tk.Scrollbar(frame2, command=text.yview)
errScroll.grid(row=3, column=1 ,sticky="ns")
errLog.config(yscrollcommand=errScroll.set)

# Создаем кнопку для запуска и остановки чтения данных из порта с помощью tkinter.Button
start_button = tk.Button(frame2, text="Запустить", command=toggle_read)
start_button.grid(row=4, column=0)

# Создаем кнопку для сохранения настроек
save_button = tk.Button(frame2, text="Save settings", command=save_settings)
save_button.grid(row=4, column=1)


# Привязываем обработчик сворачивания окна программы к событию Unmap
root.bind("<Unmap>", lambda event: minimize_to_tray())


# Подключаемся к базе данных MySQL с помощью mysql.connector.connect
try:
    sql_conn = mysql.connector.connect(user=user_name.get(), password=password.get(),
                                       host=server_name.get(),
                                       database=database_name.get(),
                                       ) #ssl_disabled=True
except mysql.connector.Error as err:
    messagebox.showinfo("Ошибка подключения SQL", format(err))
    print("Ошибка подключения SQL" + format(err) + '\n')
else:
    cursor = sql_conn.cursor()


# Запускаем функцию для чтения и записи данных из порта в базу данных
read_and_write()


# Запускаем главный цикл обработки событий окна программы
root.mainloop()
