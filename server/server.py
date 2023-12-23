#!usr/bin/python
#-*- coding: utf-8 -*-

import os
import sys
import random
import socket
import string
import threading

ip = ""
port = 27575

number_maximum_lenght = 10

numbers = []

clients = []

addresses = []

usernames = []

numbers_connect = []

banned_ips = []

def generate_random_string(length):
	chars = "qwertyuiopasdfghjklzxcvbnm1234567890"
	random_string = "".join(random.choices(chars, k=length))
	return random_string

def kick(client, address, reason):
	client.send("REQUEST=KICKED:" + reason)
	client.close()

	print(f"[LOG] {address[0]}:{address[1]} kicked for a reason: " + reason)

def ban(client, address, reason):
	file = open("banned_ip.txt", "a")
	file.write(address[0] + "\n")
	file.close()

	kick(client, address, "You have been banned!")

	print(f"[LOG] {address[0]}:{address[1]} banned for a reason: " + reason)

def amount(): #Количество подключённых пользователей
	amount = 0

	for client in clients:
		amount += 1

	return amount

def list(): #Список подключённых пользователей
	for number in numbers:
		print(number + ", ", end="")

def send_message(message, number_connect): #Отправка сообщения отдельному пользователю
	try:
		if number_connect in numbers:
			number_connect_index = numbers.index(number_connect)
			client_data = clients[number_connect_index]
			client_data.send(message)
	except Exception as error:
		print(error)

def broadcast(message): #Отправка сообщения всем пользователям
	for client in clients:
		client.send(message.encode("utf-8"))

	print("[LOG] Broadcast message sended")

def handle(client, address, number): #Пользователь
	try:
		data = client.recv(1024).decode("utf-8")

		number_lenght = len(data)

		if number_lenght == number_maximum_lenght: #Проверка длины номера
			number_connect = data
			numbers_connect.append(number_connect)
		else:
			kick(client, address, "The number is too long or short!")

		client.send("REQUEST=WAITING".encode("utf-8"))

		n = True

		while n == True:
			if number in numbers_connect:
				if number_connect in numbers_connect:
					client.send("REQUEST=SUCCESFUL_CHANNEL_CREATED".encode("utf-8"))

					numbers.append(number)
					clients.append(client)
					addresses.append(address)

					print(f"[LOG] {address[0]}:{address[1]} connected to channel")

					n = False
	
		public_key = client.recv(4096)

		if number_connect in numbers:
			number_connect_index = numbers.index(number_connect)
			client_data = clients[number_connect_index]
			client_data.send(public_key)
	except Exception as error:
		print(error)
		print(f"[LOG] {address[0]}:{address[1]} disconnected")

		try:
			numbers.remove(number)
			clients.remove(client)
			addresses.remove(address)
			client.close()
		except:
			pass

		return False

	while True:
		try:
			message = client.recv(1024)

			send_message(message, number_connect)
		except:
			print(f"[LOG] {address[0]}:{address[1]} disconnected")

			try:
				numbers.remove(number)
				clients.remove(client)
				addresses.remove(address)
				client.close()
			except:
				pass

			break

file = open("banned_ips.txt", "r")
lines = file.readlines()
file.close()

for line in lines:
	banned_ip = line.replace("\n", "")
	banned_ips.append(banned_ip)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((ip, port))
server.listen()

print("[INFO] Server started!")

print("[INFO] IP: " + ip)
print("[INFO] PORT: " + str(port))

while True: #Основной цикл сервера
	client, address = server.accept()

	print(f"[LOG] {address[0]}:{address[1]} connected ")

	if address[0] in banned_ips:
		kick(client, address, "You have been banned!")
	elif address in addresses:
		print(f"[ERROR] User {address[0]}:{address[1]} already connected.")
		kick(client, address, "You already connected!")

	client.send("REQUEST=SUCCESFUL_AUTH".encode("utf-8"))

	check = True

	while check == True:
		number = generate_random_string(10) #Генерация номера пользователя

		if number not in numbers:
			check = False

	client.send(number.encode("utf-8"))

	threading.Thread(target=handle, daemon=True, args=(client, address, number)).start()