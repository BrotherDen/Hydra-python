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
from threading import Thread
import time
import requests

soundname = 'sound.wav'  # имя звукового файла для воспроизведения


class TaskBarIcon(wx.adv.TaskBarIcon):
    """Класс для работы с иконкой в системном трее"""

    def __init__(self, parent):
        super(TaskBarIcon, self).__init__()
        self.parent = parent
        self.set_icon("icon_off.png")  # Укажи путь к иконке
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_restore)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        menu.Append(wx.ID_EXIT, 'Выход')
        self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)
        return menu

    def set_icon(self, path):
        icon = wx.Icon(path)
        self.SetIcon(icon, "Hydroponics")

    def on_restore(self, event):
        self.parent.show_window()

    def on_exit(self, event):
        wx.CallAfter(self.parent.quit)


class SerialReader(Thread):
    """Поток для чтения данных из последовательного порта"""

    def __init__(self, serial_port, callback):
        super().__init__()
        self.serial_port = serial_port
        self.callback = callback
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            if self.serial_port.is_open:
                try:
                    data = self.serial_port.readline().decode('utf-8').strip()
                    self.callback(data)
                except (serial.SerialException, UnicodeDecodeError) as err:
                    print(f"Error reading from serial port: {err}")
            time.sleep(1)  # Чтобы избежать блокировки интерфейса

    def stop(self):
        self.running = False


class App:
    def __init__(self, root):
        self.server_name = tk.StringVar()
        self.database_name = tk.StringVar()
        self.table_name = tk.StringVar()
        self.db_user_name = tk.StringVar()
        self.password = tk.StringVar()
        self.mqtt_broker = tk.StringVar()
        self.mqtt_port = tk.StringVar()
        self.mqtt_topic = tk.StringVar()
        self.mqtt_username = tk.StringVar()
        self.mqtt_password = tk.StringVar()
        self.victoria_url = tk.StringVar()

        self.root = root
        self.serial_port = None
        self.serial_reader = None
        self.setup_gui()
        self.mqtt_client = None
        self.sql_conn = None
        self.cursor = None
        self.reading = False
        self.corrected_once = False

        # Создаем wx.App для работы с системным треем
        self.wx_app = wx.App(False)
        self.tray_icon = TaskBarIcon(self)
        Thread(target=self.wx_app.MainLoop).start()

        # Обработка нажатия на системную кнопку "Свернуть"
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.root.bind("<Unmap>", self.on_minimize)  # Обрабатываем сворачивание окна

    def on_minimize(self, event):
        """Сворачивание в трей при нажатии на кнопку 'Свернуть'"""
        if self.root.state() == "iconic":  # Проверяем, что окно свернуто
            self.minimize_to_tray()

    def minimize_to_tray(self):
        """Сворачивание приложения в системный трей"""
        self.root.withdraw()  # Скрываем окно

    def show_window(self):
        """Возвращение приложения из системного трея"""
        self.root.deiconify()  # Восстанавливаем окно
        self.root.state("normal")  # Возвращаем нормальный размер окна

    def quit(self):
        """Выход из приложения"""
        self.tray_icon.RemoveIcon()  # Убираем иконку из трея
        self.root.quit()  # Закрываем окно

    def playSound(self):
        data_aud, fs = sf.read(soundname)
        sd.play(data_aud, fs)
        sd.wait()

    def load_settings(self):
        """Загрузка настроек"""
        config = configparser.ConfigParser()
        try:
            config.read('settings.ini')
            self.server_name.set(config['DEFAULT']['server_name'])
            self.database_name.set(config['DEFAULT']['database_name'])
            self.table_name.set(config['DEFAULT']['table_name'])
            self.db_user_name.set(config['DEFAULT']['db_user_name'])
            self.password.set(config['DEFAULT']['password'])
            self.port_var.set(config['DEFAULT']['port_name'])
            self.baudrate_var.set(config['DEFAULT']['baudrate'])
            self.file_entry.insert(0, config['DEFAULT']['file_name'])
            self.mqtt_broker.set(config['DEFAULT']['mqtt_broker'])
            self.mqtt_port.set(config['DEFAULT']['mqtt_port'])
            self.mqtt_topic.set(config['DEFAULT']['mqtt_topic'])
            self.mqtt_username.set(config['DEFAULT']['mqtt_username'])
            self.mqtt_password.set(config['DEFAULT']['mqtt_password'])
            self.victoria_url.set(config['DEFAULT']['victoria_url'])

            print("Settings loaded successfully.")
        except (configparser.Error, FileNotFoundError):
            print("Error loading settings or file not found, using defaults.")

    def save_settings(self):
        """Сохранение настроек"""
        config = configparser.ConfigParser()
        config['DEFAULT'] = {
            'server_name': self.server_name.get(),
            'database_name': self.database_name.get(),
            'table_name': self.table_name.get(),
            'db_user_name': self.db_user_name.get(),
            'password': self.password.get(),
            'port_name': self.port_var.get(),
            'baudrate': self.baudrate_var.get(),
            'file_name': self.file_entry.get(),
            'mqtt_broker': self.mqtt_broker.get(),
            'mqtt_port': self.mqtt_port.get(),
            'mqtt_topic': self.mqtt_topic.get(),
            'mqtt_username': self.mqtt_username.get(),
            'mqtt_password': self.mqtt_password.get(),
            'victoria_url': self.victoria_url.get()
        }
        try:
            with open('settings.ini', 'w') as f:
                config.write(f)
            print("Settings saved successfully.")
        except IOError as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def create_widgets(self):
        """Создание элементов интерфейса"""
        # Порт
        tk.Label(self.frame1, text="Port", width=10).grid(row=0, column=0)
        tk.OptionMenu(self.frame1, self.port_var, *self.port_list).grid(row=0, column=1)

        # Скорость передачи данных
        tk.Label(self.frame1, text="Baudrate", width=10).grid(row=0, column=2)
        baudrate_list = ["300", "600", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]
        tk.OptionMenu(self.frame1, self.baudrate_var, *baudrate_list).grid(row=0, column=3)

        # Поля ввода файла
        self.file_entry = tk.Entry(self.frame2, width=60)
        self.file_entry.grid(row=1, column=0)
        tk.Button(self.frame2, text="...", command=self.select_file, width=2).grid(row=1, column=1)

        # Поля вывода и лога ошибок
        self.text = tk.Text(self.frame2, width=45)
        self.text.grid(row=2, column=0)
        self.scrollbar = tk.Scrollbar(self.frame2, command=self.text.yview)
        self.scrollbar.grid(row=2, column=1, sticky="ns")
        self.text.config(yscrollcommand=self.scrollbar.set)

        self.errLog = tk.Text(self.frame2, width=45, height=7)
        self.errLog.grid(row=3, column=0)
        self.errScroll = tk.Scrollbar(self.frame2, command=self.errLog.yview)
        self.errScroll.grid(row=3, column=1, sticky="ns")
        self.errLog.config(yscrollcommand=self.errScroll.set)

        # Кнопки управления
        self.start_button = tk.Button(self.frame2, text="Запустить", command=self.toggle_read)
        self.start_button.grid(row=4, column=0)
        self.save_button = tk.Button(self.frame2, text="Save settings", command=self.save_settings)
        self.save_button.grid(row=4, column=1)

    def setup_gui(self):
        """Инициализация графического интерфейса"""
        self.frame1 = ttk.Frame(self.root)
        self.frame1.pack(fill=tk.BOTH, expand=True)

        self.frame2 = ttk.Frame(self.root)
        self.frame2.pack(fill=tk.BOTH, expand=True)

        # Порты и скорости
        self.port_var = tk.StringVar(self.frame1)
        self.baudrate_var = tk.StringVar(self.frame1)
        self.baudrate_var.set("9600")
        self.port_list = self.get_ports()

        # Если список не пустой, устанавливаем первый порт по умолчанию
        if self.port_list:
            self.port_var.set(self.port_list[0])

        self.create_widgets()
        self.load_settings()

    def get_ports(self):
        """Получение доступных последовательных портов"""
        return [port.device for port in serial.tools.list_ports.comports()]

    def open_port(self):
        """Открытие последовательного порта"""
        port = self.port_var.get()
        baudrate = int(self.baudrate_var.get())
        try:
            self.serial_port = serial.Serial(port, baudrate)
            self.serial_reader = SerialReader(self.serial_port, self.on_data_received)
            self.serial_reader.start()
        except serial.SerialException as err:
            self.playSound()
            print(f"Error: {err}")
            messagebox.showinfo("Ошибка открытия порта")

    # Создаем функцию для выбора файла из диалога
    def select_file(self):
        # Отображаем диалог выбора файла и получаем имя выбранного файла
        file_name = fd.askopenfilename()
        if file_name:  # если файл был выбран
            self.file_entry.delete(0, tk.END)  # очищаем текстовое поле
            self.file_entry.insert(0, file_name)  # вставляем имя файла в текстовое поле

    def connect_to_database(self):
        """Подключение к базе данных MySQL"""
        try:
            self.sql_conn = mysql.connector.connect(
                host=self.server_name.get(),
                database=self.database_name.get(),
                user=self.db_user_name.get(),
                password=self.password.get()
            )
            if self.sql_conn.is_connected():
                print("Successfully connected to MySQL database")
                self.cursor = self.sql_conn.cursor()
            else:
                print("Failed to connect to MySQL")
        except mysql.connector.Error as err:
            self.playSound()
            print(f"Error while connecting to MySQL: {err}")
            self.sql_conn = None

    """
    def connect_to_mqtt(self):
        #Подключение к MQTT брокеру
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.username_pw_set(self.mqtt_username.get(), self.mqtt_password.get())
            self.mqtt_client.connect(self.mqtt_broker.get(), int(self.mqtt_port.get()), 60)
            self.mqtt_client.subscribe(self.mqtt_topic.get())

            time.sleep(1)  # Задержка для установления соединения

            if not self.mqtt_client.is_connected():
                raise ConnectionError("Failed to connect to MQTT broker")

            print("Successfully connected to MQTT broker")
            return self.mqtt_client

        except Exception as err:
            self.playSound()
            print(f"Error while connecting to MQTT broker: {err}")
            return None
    """

    def connect_to_mqtt(self):
        """Подключение к MQTT брокеру с улучшенной обработкой ошибок и проверкой соединения"""
        try:
            # Инициализация клиента MQTT
            self.mqtt_client = mqtt.Client()

            # Установка учетных данных
            self.mqtt_client.username_pw_set(self.mqtt_username.get(), self.mqtt_password.get())

            # Функция обратного вызова для успешного соединения
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    print("Successfully connected to MQTT broker")
                    self.mqtt_client.subscribe(self.mqtt_topic.get())  # Подписываемся на топик
                else:
                    raise ConnectionError(f"Connection failed with result code {rc}")

            # Привязываем функцию обратного вызова к клиенту
            self.mqtt_client.on_connect = on_connect

            # Подключение к брокеру
            self.mqtt_client.connect(self.mqtt_broker.get(), int(self.mqtt_port.get()), 60)

            # Запуск фонового потока для обслуживания сетевых событий MQTT (неблокирующий)
            self.mqtt_client.loop_start()

            # Проверка на успешное соединение в течение заданного времени (например, 5 секунд)
            timeout = 5
            elapsed = 0
            while not self.mqtt_client.is_connected():
                time.sleep(0.5)
                elapsed += 0.5
                if elapsed >= timeout:
                    raise ConnectionError("Timeout while trying to connect to MQTT broker")

            return self.mqtt_client

        except Exception as err:
            self.playSound()
            print(f"Error while connecting to MQTT broker: {err}")
            return None

    def disconnect_from_database(self):
        """Отключение от базы данных MySQL"""
        if self.sql_conn is not None and self.sql_conn.is_connected():
            self.cursor.close()
            self.sql_conn.close()
            self.sql_conn = None
            print("Disconnected from MySQL database")

    def disconnect_from_mqtt(self):
        """Отключение от MQTT брокера"""
        if self.mqtt_client is not None:
            self.mqtt_client.loop_stop()  # Останавливаем цикл обработки MQTT
            self.mqtt_client.disconnect()
            self.mqtt_client = None
            print("Disconnected from MQTT broker")

    def save_to_file(self, data):
        """Сохранение данных в файл"""
        file_name = self.file_entry.get()
        if file_name:
            with open(file_name, 'a') as f:
                record = ','.join(data)
                f.write(record + "\n")
                f.close()

    def save_to_db(self, data):
        """Сохранение данных в базу данных"""
        if self.sql_conn:
            Time, Humidity, Pressure, Alt, AirTemp, WaterTemp, Salinity = data
            sql = "INSERT INTO Meteo (Time,Humidity,Pressure,Alt,AirTemp,WaterTemp,Salinity)" \
                  "  VALUES (FROM_UNIXTIME(%s), %s, %s, %s, %s, %s, %s)"
            val = (Time, Humidity, Pressure, Alt, AirTemp, WaterTemp, Salinity)
            try:
                cursor = self.sql_conn.cursor()
                cursor.execute(sql, val)
                self.sql_conn.commit()
            except mysql.connector.Error as err:
                self.playSound()
                messagebox.showinfo("Ошибка SQL", format(err))
                self.errLog.insert('end', "Ошибка SQL" + format(err) + '\n')
                print(f"Ошибка SQL: {err}")
    """
    def publish_to_mqtt(self, data):
        #Публикация данных на MQTT-брокер
        topic = self.mqtt_topic.get()
        if self.mqtt_client is not None:
            try:
                payload = json.dumps(data)  # Преобразуем данные в формат JSON
                self.mqtt_client.publish(topic, payload)
                # print(f"Published to MQTT: {payload}")
            except Exception as err:
                self.playSound()
                print(f"Error while publishing to MQTT: {err}")
        else:
            print("MQTT client is not connected.")
    """


    def publish_to_mqtt(self, data):
        """Публикация данных на MQTT-брокер"""
        if self.mqtt_client is not None:
            if not self.mqtt_client.is_connected():
                print("MQTT client is not connected.")
                return

            try:
                topic = self.mqtt_topic.get()
                payload = json.dumps(data)  # Преобразуем данные в формат JSON
                result = self.mqtt_client.publish(topic, payload)

                # Ждем завершения публикации
                result.wait_for_publish()

                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    print(f"Failed to publish to MQTT: {mqtt.error_string(result.rc)}")
                    self.playSound()

            except Exception as err:
                self.playSound()
                print(f"Error while publishing to MQTT: {err}")
        else:
            print("MQTT client is not initialized.")


    def save_to_victoria(self, data):
        """
        Форматирует данные в формате Influx Line Protocol для отправки в VictoriaMetrics
        :param data: Список данных [Time, Humidity, Pressure, Alt, AirTemp, WaterTemp, Salinity]
        :return: Строка в формате Influx Line Protocol
        """
        # Пример: замена Time на timestamp и формирование строки для поля данных
        time_unix_ns = int(data[0]) * 1_000_000_000  # Переводим время в наносекунды
        fields = f"Humidity={data[1]},Pressure={data[2]},Alt={data[3]},AirTemp={data[4]},WaterTemp={data[5]},Salinity={data[6]}"

        """захардкожен сезон"""
        transmit_line = f"Pepper,year=2024 {fields} {time_unix_ns}"
        # print (influx_line)
        try:
            response = requests.post(f"{self.victoria_url.get()}/write", data=transmit_line)

            # Проверка на успешную отправку
            if not (response.status_code == 204):
                print("Error sending data to VictoriaMetrics")
        except requests.exceptions.RequestException as err:
            # Обработка всех исключений requests
            self.playSound()
            print(f"An error occurred: {err}")

    def toggle_read(self):
        """Запуск и остановка чтения данных"""
        if self.reading:
            self.reading = False
            self.tray_icon.set_icon("icon_off.png")
            self.start_button.config(text="Запустить")

            self.serial_reader.stop()  # Останавливаем поток безопасно
            self.serial_port.close()  # Закрываем порт
            self.serial_reader = None  # Обнуляем объект потока

            self.disconnect_from_database()
            self.disconnect_from_mqtt()
        else:
            self.reading = True
            self.tray_icon.set_icon("icon_on.png")
            self.start_button.config(text="Остановить")

            self.open_port()
            self.connect_to_database()
            self.connect_to_mqtt()

    def on_data_received(self, data):
        """Обработка полученных данных"""
        if data:
            self.text.insert('end', data + '\n')
            self.text.see('end')
            self.process_data(data)

            # self.save_to_file(data)
            # self.save_to_db(data)

    # проверяем ошибку метки времени и при необходимости корректируем
    def check_time(self, data_timestamp):
        # Получаем текущее время
        current_timestamp = int(datetime.now().timestamp())  # Текущее время в секундах
        # print(datetime.fromtimestamp(int(current_timestamp)).strftime('%m-%d %H:%M:%S'))

        # Сверяем метку времени данных с текущим временем
        time_difference = abs(current_timestamp - int(data_timestamp))
        max_allowed_difference = 60  # Например, разрешаем разницу в 60 секунд

        if time_difference > max_allowed_difference:
            print(f"Внимание: разница во времени {time_difference} секунд!")
            # Корректируем время, отправляя данные в формате ГГГГММДДЧЧММСС (20230325104300)
            # по UTC!
            current_time = datetime.utcnow()
            formatted_time = current_time.strftime('%Y%m%d%H%M%S')
            self.serial_port.write(formatted_time.encode())
        else:
            print("Метка времени в пределах допустимого диапазона.")
            self.corrected_once = True

    def validate_data(self, data):
        """Проверяет данные и возвращает кортеж (валидны ли данные, откорректированные данные)."""
        data = data.split(',')
        if len(data) != 7:
            self.playSound()
            return False, None

        corrected_data = []
        for x in data:
            try:
                float(x)  # Проверяем, можно ли преобразовать в float
                corrected_data.append(x)
            except ValueError:
                self.playSound()
                # Если не удалось преобразовать, данные невалидны
                return False, None

        # Проверка конкретных значений
        Time, Humidity, Pressure, Alt, AirTemp, WaterTemp, Salinity = corrected_data

        if not self.corrected_once:
            self.check_time(Time)
            return False, None

        # Проверка диапазонов
        if not (0 <= int(Humidity) <= 100 and
                0 <= float(AirTemp) <= 50 and
                0 <= float(WaterTemp) <= 50 and
                0 <= int(Salinity) <= 3000):
            return False, None
        else:
            # устраняем сбой датчика,если есть
            if float(WaterTemp) == -127.0:
                # Воспроизводим звуковой файл и корректируем данные
                self.playSound()
                corrected_data[5] = 25.03  # WaterTemp
                corrected_data[6] = int(float(Salinity) * (1.0 + 0.02 * (-127.0 - 25.0)))  # Salinity
            return True, corrected_data

    def process_data(self, data):
        """Проверяет данные, воспроизводит звук при ошибке и при необходимости корректирует данные."""
        valid, corrected_data = self.validate_data(data)

        if not valid:
            # Воспроизводим звуковой файл для невалидных данных
            self.playSound()
            print('Ошибка в данных')
            return

        # Выводим данные на экран для отладки
        print(datetime.fromtimestamp(int(corrected_data[0])).strftime('%m-%d %H:%M:%S'),
              corrected_data[1], corrected_data[2], corrected_data[3],
              corrected_data[4], corrected_data[5], corrected_data[6])

        # записываем во все хранилища
        self.save_to_file(corrected_data)
        self.save_to_db(corrected_data)
        self.publish_to_mqtt(corrected_data)
        self.save_to_victoria(corrected_data)

        # Time, Humidity, Pressure, Alt, AirTemp, WaterTemp, Salinity = corrected_data


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
