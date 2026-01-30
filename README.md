# CLI Agent

Задать репозиторий, чьи issues будут прасматриваться и разбираться, необходимо в файле .env. Там же указывается GIT_TOKEN и API_KEY (на данный момент из провайдеров реализовано взаимодействие только с Openrouter). Пример файла в репозитории представлен.

Чтобы запустить процесс через консоль необходимо произвести следующие действия: склонировать репозиторий, выполнить python main.py run. В данном случае агент будет работать с уже имеющимися и вновь создаваемыми issues ровно до этапа его остановки.

<img width="887" height="318" alt="image" src="https://github.com/user-attachments/assets/8e094284-a574-4796-81e2-5e24528206c9" />

Также придусмотрены опции для обработки конкретного issue или pr.

Созданный для собственного тестового репозитория при ограничении в 1 итерацию (количество также задаётся в .env файле) PR:
<img width="1295" height="994" alt="image" src="https://github.com/user-attachments/assets/dedfa4b5-e380-442c-924a-2b2471c5d8fc" />

Пример исправленного файла:
<img width="1326" height="910" alt="image" src="https://github.com/user-attachments/assets/ea08f63b-63f8-49fc-bedc-f8c86add2099" />

Сам issue после обработки:
<img width="1341" height="1020" alt="image" src="https://github.com/user-attachments/assets/97e694ad-6725-4c5f-91ce-c8539733a5fc" />



Ссылка на виде: https://drive.google.com/file/d/1dWcgbL7uYWzYBBN-vjc1IjEIS4xWmmDC/view?usp=sharing
