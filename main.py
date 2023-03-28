#import bluetooth
import mysql.connector
import tkinter as tk
import os
import sys
import time
from PIL import Image, ImageTk
import threading
import win32api
import win32con
import win32gui

# Подключение к базе данных
mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  database="Meteo"
)

# Открытие курсора
mycursor = mydb.cursor()

# Очистка таблицы Hydra
#mycursor.execute("TRUNCATE TABLE Hydra")

# # Проверка доступности порта Bluetooth
# nearby_devices = bluetooth.discover_devices()
# for bdaddr in nearby_devices:
#     if bdaddr == '00:11:22:33:44:55':
#         print("Порт Bluetooth доступен")
#         status_label_text = "Подключено"
#         icon_path = "connected.ico"
#         break
# else:
#     print("Порт Bluetooth недоступен")
#     status_label_text = "Не подключено"
#     icon_path = "disconnected.ico"

# Функция для записи данных в базу данных
def write_to_database():
    # Считывание строки из порта
    line = ser.readline().decode('utf-8').strip()

    # Разделение строки на значения
    values = line.split(',')

    # Вставка значений в таблицу Hydra
    sql = "INSERT INTO Hydra (temperature, humidity) VALUES (%s, %s)"
    val = (values[0], values[1])
    mycursor.execute(sql, val)
    mydb.commit()

    # Запись данных каждые 5 секунд
    root.after(5000, write_to_database)

# Функция для сворачивания программы в трей
def minimize_to_tray():
    # Создание окна
    window = tk.Toplevel()
    window.geometry("0x0")

    # Скрытие окна
    root.withdraw()

    # Создание иконки в трее
    icon = Image.open(icon_path)
    icon = icon.resize((16, 16), Image.ANTIALIAS)
    icon = ImageTk.PhotoImage(icon)
    tray_icon = tk.Label(window, image=icon)
    tray_icon.image = icon
    tray_icon.pack()

    # Функция для отображения окна при двойном щелчке на иконке в трее
    def show_window(event=None):
        window.destroy()
        root.deiconify()

    # Привязка функции к событию двойного щелчка на иконке в трее
    tray_icon.bind("<Double-Button-1>", show_window)

    # Отображение иконки в трее
    def show_tray_icon():
        nid = (window.winfo_id(), 0, win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP)
        nid_icon = (hinst, 0, win32con.RES_ICON, icon_path, 0, "")
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid + nid_icon)

    # Удаление иконки из трея
    def remove_tray_icon():
        nid = (window.winfo_id(), 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)

    # Отображение иконки в трее