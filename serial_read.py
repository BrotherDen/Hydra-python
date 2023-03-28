import serial
import mysql.connector

# Открываем последовательный порт COM5
serial_port = serial.Serial('COM5', 9600)

# Пытаемся открыть последовательный порт COM5
try:
    serial_port = serial.Serial('COM5', 9600)
except serial.SerialException:
    # Если порт недоступен, выводим сообщение об ошибке и завершаем программу
    print("Порт COM5 недоступен.")
    exit()

# Подключаемся к базе данных MySQL
sql_conn = mysql.connector.connect(host='localhost', user='root', password='', database='Hydra')
cursor = sql_conn.cursor()

# Читаем данные из порта в бесконечном цикле
while True:
    # Считываем одну строку данных
    data = serial_port.readline()

    print (data)

    # Преобразуем данные в строковый формат
    data = data.decode('utf-8')

    # Разделяем данные по запятым
    data = data.split(',')

    # Извлекаем температуру и влажность из данных
    AirTemp = data[5]
    Humidity = data[2]

    print(Humidity,AirTemp)

    # Записываем температуру и влажность в таблицу Meteo
    cursor.execute("INSERT INTO Meteo (AirTemp, Humidity) VALUES (%s, %s)", (temperature, humidity))

    # Сохраняем изменения в базе данных
    sql_conn.commit()