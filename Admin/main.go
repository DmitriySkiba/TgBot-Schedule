package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/golang-jwt/jwt"
	"github.com/gorilla/mux"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type UserData struct {
	Id   int64  `json:"id"`
	Name string `json:"name"`
}

type About struct {
	Name  string `bson:"username"`
	Group string `bson:"group"`
}

type User struct {
	GithubID int64  `bson:"github_id"`
	Role     string `bson:"role"`
	About    About  `bson:"about"`
}

type RegUser struct {
	GitId  int64  `json:"github_id"`
	ChatId string `json:"chat_id"`
	Role   string `json:"role"`
	Name   string `json:"username"`
	Group  string `json:"group"`
}

// Данные GitHub приложения
const (
	CLIENT_ID       = "ed94f62ab2f5d86261f6"
	CLIENT_SECRET   = "629ced76531a3d1f81d9086c8f67978b8c3383ec"
	TOKEN_SECRET    = "1234"
	SCHEDULE_SECRET = "5678"
)

func main() {
	go startServer()

	bufio.NewReader(os.Stdin).ReadBytes('\n')
}

// Запуск сервера
func startServer() {
	router := mux.NewRouter()

	router.Use(enableCors)

	// Регистрируем маршруты
	router.HandleFunc("/auth", auth)                 // Бот делает запрос, к нему прикладывает chat_id, затем бот получает ссылку.
	router.HandleFunc("/oauth", handleOauth)         // Вызов функции при запросе на /oauth
	router.HandleFunc("/userdata", inputUserData)    // Ввод ФИО пользователя
	router.HandleFunc("/admin", startAdministrating) // Начало сеанса администрирования
	router.HandleFunc("/schedule", handleSchedule)   // Получение информации о расписании

	http.ListenAndServe(":8080", router) // Запуск сервера
}

// Метод middleware для разрешения CORS
func enableCors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Origin, Accept, Authorization")
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
		} else {
			next.ServeHTTP(w, r)
		}
	})
}

func auth(w http.ResponseWriter, r *http.Request) {
	chat_id := r.URL.Query().Get("chat_id")
	var authURL string = "https://github.com/login/oauth/authorize?client_id=" + CLIENT_ID + "&state=" + chat_id
	fmt.Fprintf(w, "Чтобы зайти, перейдите по ссылке:\n"+authURL)
}

// Обработчик запроса
func handleOauth(w http.ResponseWriter, r *http.Request) {
	var responseHtml = "<html><body><h1>Вы НЕ аутентифицированы!</h1></body></html>"

	code := r.URL.Query().Get("code")     // Достаем временный код из запроса
	chat_id := r.URL.Query().Get("state") // Достаем chat_id код из запроса
	if code != "" {
		accessToken := getAccessToken(code)
		userData := getUserData(accessToken)

		if !checkData(userData.Id) { //Проверяем существует ли док с таким id, если нет, то создаём док.
			register(userData.Id)
		}

		responseHtml = "<html><body><h1>Вы аутентифицированы!</h1></body></html>"

		// Подключаемся к базе, чтобы забрать статус пользователя
		clientOptions := options.Client().ApplyURI("mongodb+srv://Vladimir:pazintrul@tgbot.rnldbuj.mongodb.net/?retryWrites=true&w=majority")
		client, err := mongo.Connect(context.TODO(), clientOptions)

		if err != nil {
			log.Fatal(err)
		}

		err = client.Ping(context.TODO(), nil)
		if err != nil {
			log.Fatal(err)
		}

		collection := client.Database("TGbot").Collection("user")
		filter := bson.M{"github_id": userData.Id}

		var result User

		err = collection.FindOne(context.Background(), filter).Decode(&result)
		if err != nil {
			client.Disconnect(context.Background())
		}

		// Создать новую структуру пользователя
		user := RegUser{
			GitId:  userData.Id,
			ChatId: chat_id,
			Role:   result.Role,
			Name:   result.About.Name,
			Group:  result.About.Group,
		}

		// Сериализовать структуру пользователя в JSON
		data, err := json.Marshal(user)
		if err != nil {
			log.Fatal(err)
		}

		// Создать новый POST запрос
		resp, err := http.Post("http://localhost:8081/register", "application/json", bytes.NewBuffer(data))
		if err != nil {
			log.Fatal(err)
		}

		// Обработать ответ
		defer resp.Body.Close()

	}

	fmt.Fprint(w, responseHtml) // Ответ на запрос
}

// Меняем временный код на токен доступа
func getAccessToken(code string) string {
	// Создаём http-клиент с дефолтными настройками
	client := http.Client{}
	requestURL := "https://github.com/login/oauth/access_token"

	// Добавляем данные в виде Формы
	form := url.Values{}
	form.Add("client_id", CLIENT_ID)
	form.Add("client_secret", CLIENT_SECRET)
	form.Add("code", code)

	// Готовим и отправляем запрос
	request, _ := http.NewRequest("POST", requestURL, strings.NewReader(form.Encode()))
	request.Header.Set("Accept", "application/json") // просим прислать ответ в формате json
	response, _ := client.Do(request)

	// if response != nil {
	// 	log.Fatal(response)
	// }
	// fmt.Println("r")

	defer response.Body.Close()

	// Достаём данные из тела ответа
	var responsejson struct {
		AccessToken string `json:"access_token"`
	}
	json.NewDecoder(response.Body).Decode(&responsejson)
	return responsejson.AccessToken
}

// Получаем информацию о пользователе
func getUserData(AccessToken string) UserData {
	// Создаём http-клиент с дефолтными настройками
	client := http.Client{}
	requestURL := "https://api.github.com/user"

	// Готовим и отправляем запрос
	request, _ := http.NewRequest("GET", requestURL, nil)
	request.Header.Set("Authorization", "Bearer "+AccessToken)
	response, _ := client.Do(request)

	// if response != nil {
	// 	log.Fatal(response)
	// }

	defer response.Body.Close()

	var data UserData
	json.NewDecoder(response.Body).Decode(&data)
	return data
}

func checkData(id int64) bool {
	clientOptions := options.Client().ApplyURI("mongodb+srv://Vladimir:pazintrul@tgbot.rnldbuj.mongodb.net/?retryWrites=true&w=majority")
	client, err := mongo.Connect(context.TODO(), clientOptions)

	if err != nil {
		log.Fatal(err)
	}

	// Check the connection
	err = client.Ping(context.TODO(), nil)

	if err != nil {
		log.Fatal(err)
	}

	collection := client.Database("TGbot").Collection("user")

	filter := bson.D{{"github_id", id}}

	var result User

	err = collection.FindOne(context.TODO(), filter).Decode(&result)
	if err != nil {
		client.Disconnect(context.TODO())
		return false
	}

	return true
}

func register(userId int64) {
	clientOptions := options.Client().ApplyURI("mongodb+srv://Vladimir:pazintrul@tgbot.rnldbuj.mongodb.net/?retryWrites=true&w=majority")
	client, err := mongo.Connect(context.TODO(), clientOptions)

	if err != nil {
		log.Fatal(err)
	}

	// Check the connection
	err = client.Ping(context.TODO(), nil)

	if err != nil {
		log.Fatal(err)
	}

	collection := client.Database("TGbot").Collection("user")

	var user User

	user.GithubID = userId
	user.Role = "student"
	user.About.Name = ""
	user.About.Group = ""

	// Запись нового пользователя
	_, err = collection.InsertOne(context.TODO(), user)
	if err != nil {
		log.Fatal(err)
	}

	client.Disconnect(context.TODO())
}

func inputUserData(w http.ResponseWriter, r *http.Request) {
	clientOptions := options.Client().ApplyURI("mongodb+srv://Vladimir:pazintrul@tgbot.rnldbuj.mongodb.net/?retryWrites=true&w=majority")
	client, err := mongo.Connect(context.TODO(), clientOptions)

	if err != nil {
		log.Fatal(err)
	}

	// Check the connection
	err = client.Ping(context.TODO(), nil)

	if err != nil {
		log.Fatal(err)
	}

	collection := client.Database("TGbot").Collection("user")

	er := r.ParseForm()
	if er != nil {
		http.Error(w, "Bad Request", http.StatusBadRequest)
		return
	}

	userId, err := strconv.Atoi(r.FormValue("git_id")) // Достаем git_id из запроса
	if err != nil {
		log.Fatal()
	}
	username := r.FormValue("username") // Достаем username из запроса
	group := r.FormValue("group")       // Достаем username из запроса

	fmt.Println(userId, username, group)

	filter := bson.M{"github_id": userId}

	// Ищем пользователя
	cursor, err := collection.Find(context.Background(), filter)
	if err != nil {
		log.Fatal(err)
	}
	defer cursor.Close(context.Background())

	// Проверьте наличие документов
	if cursor.Next(context.Background()) {
		log.Println("Документы, удовлетворяющие условию, существуют")
	} else if err := cursor.Err(); err != nil {
		log.Fatal(err)
	} else {
		log.Println("Нет документов, удовлетворяющих условию")
	}
	// Обновляем ФИО и группу
	update := bson.M{"$set": bson.M{"about.username": username, "about.group": group}}

	result, err := collection.UpdateOne(context.Background(), filter, update)
	if err != nil {
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}

	if result.MatchedCount != 0 {
		fmt.Println("matched and replaced an existing document")
	} else if result.UpsertedCount != 0 {
		fmt.Printf("inserted a new document with ID %v\n", result.UpsertedID)
	}

	client.Disconnect(context.TODO())
}

func startAdministrating(w http.ResponseWriter, r *http.Request) {
	clientOptions := options.Client().ApplyURI("mongodb+srv://Vladimir:pazintrul@tgbot.rnldbuj.mongodb.net/?retryWrites=true&w=majority")
	client, err := mongo.Connect(context.TODO(), clientOptions)

	if err != nil {
		log.Fatal(err)
	}

	err = client.Ping(context.TODO(), nil)
	if err != nil {
		log.Fatal(err)
	}

	collection := client.Database("TGbot").Collection("user")

	er := r.ParseForm()
	if er != nil {
		http.Error(w, "Bad Request", http.StatusBadRequest)
		return
	}

	userId, err := strconv.Atoi(r.FormValue("git_id")) // Достаем git_id из запроса
	if err != nil {
		log.Fatal()
	}

	filter := bson.M{"github_id": userId}

	var result User

	err = collection.FindOne(context.Background(), filter).Decode(&result)
	if err != nil {
		client.Disconnect(context.Background())
	}

	// Если роль совпадает, генерируем JWT-токен
	if result.Role == "admin" {

		// Определяем время жизни токена +24 часа от момента создания
		tokenExpiresAt := time.Now().Add(time.Second * time.Duration(15))

		// Заполняем данными полезную нагрузку
		payload := jwt.MapClaims{
			"git_id":     result.GithubID,
			"role":       result.Role,
			"action":     true,
			"expires_at": tokenExpiresAt.Unix(), // Не обязательно
		}

		// Создаём токен с методом шифрования HS256
		token := jwt.NewWithClaims(jwt.SigningMethodHS256, payload)

		// Подписываем токен секретным ключом
		tokenString, err := token.SignedString([]byte(TOKEN_SECRET))

		fmt.Printf("Токен: %v\n", tokenString)
		fmt.Printf("Действителен до: %v\n", tokenExpiresAt)
		fmt.Printf("Ошибка: %v\n", err)

		fmt.Fprint(w, tokenString)

	} else {
		fmt.Fprint(w, "Недостаточно прав")
	}

	client.Disconnect(context.TODO())
}

func handleSchedule(w http.ResponseWriter, r *http.Request) {
	clientOptions := options.Client().ApplyURI("mongodb+srv://Vladimir:pazintrul@tgbot.rnldbuj.mongodb.net/?retryWrites=true&w=majority")
	client, err := mongo.Connect(context.TODO(), clientOptions)

	if err != nil {
		log.Fatal(err)
	}

	err = client.Ping(context.TODO(), nil)
	if err != nil {
		log.Fatal(err)
	}

	collection := client.Database("TGbot").Collection("user")

	er := r.ParseForm()
	if er != nil {
		http.Error(w, "Bad Request", http.StatusBadRequest)
		return
	}

	userId, err := strconv.Atoi(r.FormValue("git_id")) // Достаем git_id из запроса
	if err != nil {
		log.Fatal()
	}
	action := r.FormValue("action")

	filter := bson.M{"github_id": userId}

	var result User

	err = collection.FindOne(context.Background(), filter).Decode(&result)
	if err != nil {
		client.Disconnect(context.Background())
	}

	// Если роль совпадает, генерируем JWT-токен
	// if result.Role == "student" {

	tokenExpiresAt := time.Now().Add(time.Second * time.Duration(15))

	// Заполняем данными полезную нагрузку
	payload := jwt.MapClaims{
		"git_id":     result.GithubID,
		"role":       result.Role,
		"group":      result.About.Group,
		"action":     action,
		"expires_at": tokenExpiresAt.Unix(), // Не обязательно
	}

	// Создаём токен с методом шифрования HS256
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, payload)

	// Подписываем токен секретным ключом
	tokenString, err := token.SignedString([]byte(SCHEDULE_SECRET))

	fmt.Printf("Ошибка: %v\n", err)
	fmt.Fprint(w, tokenString)

	// } else {
	// 	fmt.Fprint(w, "Недостаточно прав")
	// }

	client.Disconnect(context.TODO())
}
