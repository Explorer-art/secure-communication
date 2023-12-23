#!usr/bin/python
#-*- coding: utf-8 -*-

import os
import sys
import time
import datetime
import socket
import threading
from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_OAEP

def clear():
	if sys.platform == "win32":
		os.system("cls")
	elif sys.platform == "linux" or sys.platform == "linux2":
		os.system("clear")

def encrypt(public_key, message):
	key = RSA.import_key(public_key)
	cipher = PKCS1_OAEP.new(key)
	encrypted_message = cipher.encrypt(message.encode("utf-8"))
	return encrypted_message

def decrypt(private_key, encrypted_message):
	key = RSA.import_key(private_key)
	cipher = PKCS1_OAEP.new(key)
	message = cipher.decrypt(encrypted_message)
	return message

def receive(client, private_key):
	while True:
		try:
			message = decrypt(private_key, client.recv(1024)).decode("utf-8")

			now = datetime.datetime.now()

			print("\n" + f"[{now.day}-{now.month}-{now.year} {now.hour}:{now.minute}:{now.second}] {message}" + "\n")
		except Exception as error:
			print("Error! " + str(error))
			client.close()
			break

def writer(client, public_key):
	while True:
		message = input("\n> ")

		if message == "!info":
			print("Информация:")
			print("Версия: 1.0")
			print("")

		if message != "":
			now = datetime.datetime.now()

			message = f"{username} > {message}"

			print(f"[{now.day}-{now.month}-{now.year} {now.hour}:{now.minute}:{now.second}] " + message)

			client.send(encrypt(public_key, message))

clear()

print("Защищённый канал связи")
print("")

username = input("Введите имя пользователя: ")
ip_address = input("Введите айпи адрес сервера к которому вы хотите подключится: ")

if ":" not in ip_address:
	ip = ip_address
	port = 27575
elif ":" in ip_address:
	ip = ip_address.split(":")[0]
	port = int(ip_address.split(":")[1])

print("Генерация ключей шифрования..")

key = RSA.generate(2048)
public_key_1 = key.publickey().export_key()
private_key = key.export_key()

print("Подключение..")

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((ip, port))

print("Авторизация..")

data = client.recv(1024).decode("utf-8")

if data[0:14] == "REQUEST=KICKED":
	reason = data[15:9999]
	print("Вы кикнуты по причине: " + reason)

	client.close()

	sys.exit()
elif data == "REQUEST=SUCCESFUL_AUTH":
	print("Авторизация успешно пройдена!")

number = client.recv(1024).decode("utf-8")

print("Ваш номер: " + number)

number_connect = input("Введите номер пользователя к которому вы хотите подключиться: ")

client.send(number_connect.encode("utf-8"))

data = client.recv(1024).decode("utf-8")

if data[0:14] == "REQUEST=KICKED":
	reason = data[15:9999]
	print("Вы кикнуты по причине: " + reason)

	client.close()

	sys.exit()

if data == "REQUEST=WAITING":
	print("Ожидание подключения пользователя..")

	data = client.recv(1024).decode("utf-8")

if data == "REQUEST=SUCCESFUL_CHANNEL_CREATED":
	client.send(public_key_1)

	public_key_2 = client.recv(4096)

	print("Успешное подключение!")

	time.sleep(2)

	clear()

	print("Защищённый канал связи")
	print("")
	print("Имя пользователя: " + username)
	print("Ваш номер: " + number)
	print("")

	receive_thread = threading.Thread(target=receive, daemon=True, args=(client, private_key))  # Получение всех сообщений
	receive_thread.start()
	writer_thread = threading.Thread(target=writer, daemon=True, args=(client, public_key_2))  # Отправка сообщений
	writer_thread.start()

while True:
	time.sleep(1)