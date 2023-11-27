package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math/rand"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/360EntSecGroup-Skylar/excelize"
	"github.com/golang-jwt/jwt"
	"github.com/gorilla/mux"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type About struct {
	Name  string `bson:"username"`
	Group string `bson:"group"`
}

type User struct {
	GithubID int64  `bson:"github_id"`
	Role     string `bson:"role"`
	About    About  `bson:"about"`
}

// Данные GitHub приложения
const (
	CLIENT_ID     = "ed94f62ab2f5d86261f6"
	CLIENT_SECRET = "629ced76531a3d1f81d9086c8f67978b8c3383ec"
	TOKEN_SECRET  = "1234"
)

var sessions map[int]string

func init() {
	// Инициализация словаря
	sessions = make(map[int]string)
}

func main() {
	go startServer()

	bufio.NewReader(os.Stdin).ReadBytes('\n')
}

// Запуск сервера
func startServer() {
	router := mux.NewRouter()

	router.Use(enableCors)

	// fs := http.FileServer(http.Dir("./static"))
	// http.Handle("/static/", http.StripPrefix("/static/", fs))
	// sm := http.NewServeMux()
	// sm.Handle("/admin/", http.StripPrefix("/admin/", fs))

	// http.PathPrefix("/admin").Handler(sm)

	// Регистрируем маршруты
	router.HandleFunc("/start-admin", startAdmin)         // Начало сеанса администрирования
	router.HandleFunc("/update-student", updateStudent)   // Обновление данных студента из админки
	router.HandleFunc("/delete-student", deleteStudent)   // Удаление студента из админки
	router.HandleFunc("/admin", enterAdmin)               // Вход в админку по ссылке
	router.HandleFunc("/get-students", getStudents)       // Получение студентов для таблицы в админке
	router.HandleFunc("/upload-schedule", uploadSchedule) // Обновление расписания из файла

	http.ListenAndServe(":8082", router) // Запуск сервера
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

func startAdmin(w http.ResponseWriter, r *http.Request) {

	er := r.ParseForm()
	if er != nil {
		http.Error(w, "Bad Request", http.StatusBadRequest)
		return
	}

	tokenString := r.FormValue("data") // Достаем username из запроса

	// Выполняем проверку токена и извелечение данных
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		// Сюда можно добавить дополнительные проверки токена
		return []byte(TOKEN_SECRET), nil
	})

	// Достаём данные из токена
	payload, ok := token.Claims.(jwt.MapClaims)
	if ok && token.Valid {
		if payload["action"] == true {
			git_id := int(payload["git_id"].(float64))
			sessions[git_id] = tokenString

			fmt.Fprint(w, "http://127.0.0.1:8082/admin?token="+tokenString)
		} else {
			fmt.Fprint(w, "У Вас нет прав на данное действие")
		}

	} else {
		fmt.Println(err)
	}
}

func enterAdmin(w http.ResponseWriter, r *http.Request) {

	code := r.URL.Query().Get("token") // Достаем временный код из запроса
	if code != "" {

		if valueExists(sessions, code) {

			// Выполняем проверку токена и извелечение данных
			token, err := jwt.Parse(code, func(token *jwt.Token) (interface{}, error) {
				// Сюда можно добавить дополнительные проверки токена
				return []byte(TOKEN_SECRET), nil
			})

			// Достаём данные из токена
			payload, ok := token.Claims.(jwt.MapClaims)
			if ok && token.Valid {
				t := int64(payload["expires_at"].(float64))

				if time.Unix(t, 0).Sub(time.Now()) > 0 {
					// Создаем новое время истечения
					newExpirationTime := time.Now().Add(15 * time.Minute)

					// Обновляем время истечения в исходном токене
					payload["expires_at"] = newExpirationTime.Unix()

					tokenString, err := token.SignedString([]byte(TOKEN_SECRET))
					if err != nil {
						fmt.Println("Ошибка при создании обновленного токена:", err)
					}

					// git_id := int(payload["git_id"].(float64))
					// sessions[git_id] = tokenString

					cookie := http.Cookie{
						Name:     "jwt_token",
						Value:    tokenString,
						Expires:  newExpirationTime,
						HttpOnly: true,
					}

					http.SetCookie(w, &cookie)

					http.ServeFile(w, r, "./static/index.html")
				} else {
					fmt.Fprint(w, "<html><body><h1>Время жизни токена истекло</h1></body></html>")
				}

			} else {
				fmt.Println(err)
			}

		} else {
			fmt.Fprint(w, "<html><body><h1>Такого пользователя не существует</h1></body></html>")
		}

	} else {

		token := generateToken(rand.Intn(2) + 3)
		sessions[1] = token
		fmt.Fprint(w, "<html><body><h1><a href='https://web.telegram.org/a/#6609893395'>Перейдите по сылке для авторизации</a></h1></body></html>")
		fmt.Fprintf(w, "<html><body><h2>Токен запроса доступа: %v</h2></body></html>", token)
	}
}

func getStudents(w http.ResponseWriter, r *http.Request) {
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

	ctx, _ := context.WithTimeout(context.Background(), 5*time.Second)

	// Делаем запрос к MongoDB для получения данных
	cursor, err := collection.Find(ctx, bson.M{})
	if err != nil {
		log.Fatal(err)
	}
	defer cursor.Close(ctx)

	// Создаем срез для хранения данных
	var data []User

	// Обрабатываем каждый документ из запроса и добавляем в срез
	for cursor.Next(ctx) {
		var d User
		if err := cursor.Decode(&d); err != nil {
			log.Fatal(err)
		}
		data = append(data, d)
	}
	if err := cursor.Err(); err != nil {
		log.Fatal(err)
	}

	// Преобразуем срез данных в JSON
	jsonData, err := json.Marshal(data)
	if err != nil {
		log.Fatal(err)
	}

	// Устанавливаем заголовки для ответа и выводим данные в ответ
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(jsonData)

	client.Disconnect(context.TODO())
}

func updateStudent(w http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie("jwt_token")
	if err == nil {
		if err == http.ErrNoCookie {
			// Кука с токеном отсутствует, выполнить требуемую логику обработки
			fmt.Fprint(w, "<html><body><h1>Доступ запрещен</h1></body></html>")

		} else {
			tokenString := cookie.Value

			// Выполняем проверку токена и извелечение данных
			token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
				// Сюда можно добавить дополнительные проверки токена
				return []byte(TOKEN_SECRET), nil
			})

			// Достаём данные из токена
			payload, ok := token.Claims.(jwt.MapClaims)
			if ok && token.Valid {
				t := int64(payload["expires_at"].(float64))

				if time.Unix(t, 0).Sub(time.Now()) > 0 && payload["action"] == true {

					// Обновление данных пользователя
					// --------------------------------------------------------/
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

					// Достаем данные из запроса
					userId, err := strconv.Atoi(r.FormValue("git_id"))
					if err != nil {
						log.Fatal()
					}
					username := r.FormValue("username")
					group := r.FormValue("group")
					role := r.FormValue("role")

					fmt.Println(userId, username, group, role)

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
					// Обновляем данные студента
					update := bson.M{"$set": bson.M{"role": role, "about.username": username, "about.group": group}}

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
					// --------------------------------------------------------/

					// Создаем новое время истечения
					newExpirationTime := time.Now().Add(15 * time.Minute)
					payload["expires_at"] = newExpirationTime.Unix()

					newTokenString, err := token.SignedString([]byte(TOKEN_SECRET))
					if err != nil {
						fmt.Println("Ошибка при создании обновленного токена:", err)
					}

					cookie := http.Cookie{
						Name:     "jwt_token",
						Value:    newTokenString,
						Expires:  newExpirationTime,
						HttpOnly: true,
					}

					http.SetCookie(w, &cookie)

					http.ServeFile(w, r, "./static/index.html")
				} else {
					fmt.Fprint(w, "<html><body><h1>Время жизни токена истекло</h1></body></html>")
				}

			} else {
				fmt.Println(err)
			}

		}

	} else {
		fmt.Println(err)
	}
}

func deleteStudent(w http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie("jwt_token")
	if err == nil {
		if err == http.ErrNoCookie {
			// Кука с токеном отсутствует, выполнить требуемую логику обработки
			fmt.Fprint(w, "<html><body><h1>Доступ запрещен</h1></body></html>")

		} else {
			tokenString := cookie.Value

			// Выполняем проверку токена и извелечение данных
			token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
				// Сюда можно добавить дополнительные проверки токена
				return []byte(TOKEN_SECRET), nil
			})

			// Достаём данные из токена
			payload, ok := token.Claims.(jwt.MapClaims)
			if ok && token.Valid {
				t := int64(payload["expires_at"].(float64))

				if time.Unix(t, 0).Sub(time.Now()) > 0 && payload["action"] == true {

					// Обновление данных пользователя
					// --------------------------------------------------------/
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

					// Достаем данные из запроса
					userId, err := strconv.Atoi(r.FormValue("git_id"))
					if err != nil {
						log.Fatal()
					}

					filter := bson.M{"github_id": userId}

					result, err := collection.DeleteOne(context.TODO(), filter)
					if err != nil {
						log.Fatal(err)
					}

					log.Printf("Удалено документов: %d", result.DeletedCount)
					// --------------------------------------------------------/

					// Создаем новое время истечения
					newExpirationTime := time.Now().Add(15 * time.Minute)
					payload["expires_at"] = newExpirationTime.Unix()

					newTokenString, err := token.SignedString([]byte(TOKEN_SECRET))
					if err != nil {
						fmt.Println("Ошибка при создании обновленного токена:", err)
					}

					cookie := http.Cookie{
						Name:     "jwt_token",
						Value:    newTokenString,
						Expires:  newExpirationTime,
						HttpOnly: true,
					}

					http.SetCookie(w, &cookie)

					http.ServeFile(w, r, "./static/index.html")
				} else {
					fmt.Fprint(w, "<html><body><h1>Время жизни токена истекло</h1></body></html>")
				}

			} else {
				fmt.Println(err)
			}

		}

	} else {
		fmt.Println(err)
	}
}

func uploadSchedule(w http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie("jwt_token")
	if err == nil {
		if err == http.ErrNoCookie {
			// Кука с токеном отсутствует, выполнить требуемую логику обработки
			fmt.Fprint(w, "<html><body><h1>Доступ запрещен</h1></body></html>")

		} else {
			tokenString := cookie.Value

			// Выполняем проверку токена и извелечение данных
			token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
				return []byte(TOKEN_SECRET), nil
			})

			// Достаём данные из токена
			payload, ok := token.Claims.(jwt.MapClaims)
			if ok && token.Valid {
				t := int64(payload["expires_at"].(float64))

				if time.Unix(t, 0).Sub(time.Now()) > 0 && payload["action"] == true {

					// Принимаем файл из формы
					// --------------------------------------------------------/
					file, handler, err := r.FormFile("file")
					if err != nil {
						log.Println("Ошибка при получении файла:", err)
					}
					defer file.Close()

					f, err := os.Create(handler.Filename)
					if err != nil {
						log.Println("Ошибка при создании временного файла:", err)
					}
					defer f.Close()

					_, err = io.Copy(f, file)
					if err != nil {
						log.Println("Ошибка при сохранении файла:", err)
					}

					err = parseExcelToJson(f.Name(), w)
					if err != nil {
						log.Println("Ошибка при преобразовании файла Excel в JSON:", err)
					}
					// --------------------------------------------------------/

					newExpirationTime := time.Now().Add(15 * time.Minute)
					payload["expires_at"] = newExpirationTime.Unix()

					newTokenString, err := token.SignedString([]byte(TOKEN_SECRET))
					if err != nil {
						fmt.Println("Ошибка при создании обновленного токена:", err)
					}

					cookie := http.Cookie{
						Name:     "jwt_token",
						Value:    newTokenString,
						Expires:  newExpirationTime,
						HttpOnly: true,
					}

					http.SetCookie(w, &cookie)

					http.ServeFile(w, r, "./static/index.html")
				} else {
					fmt.Fprint(w, "<html><body><h1>Время жизни токена истекло</h1></body></html>")
				}

			} else {
				fmt.Println(err)
			}

		}

	} else {
		fmt.Println(err)
	}
}

func parseExcelToJson(filename string, w http.ResponseWriter) error {
	f, err := excelize.OpenFile(filename)
	if err != nil {
		return err
	}

	rows := f.GetRows("Лист1")

	var data []map[string]interface{}
	item := make(map[string]interface{})

	// Четная/нечетная неделя
	for _, key := range rows[0] {
		item[key] = make(map[string]interface{})
	}
	delete(item, "")

	// Группы
	for group := range item {
		cur := convertInterfaceToMap(item[group])
		for _, key := range rows[1] {
			cur[key] = make(map[string]interface{})

			// Дни недели
			days := convertInterfaceToMap(cur[key])
			for ind, arr := range rows[1:] {
				if ind%6 == 1 {
					for _, key := range arr {
						days[key] = make(map[string]interface{})

						// Предметы
						classes := convertInterfaceToMap(days[key])
						for _, row := range rows[ind+1 : ind+7] {
							classes[row[0]] = map[string]string{
								"Предмет":     row[1],
								"Аудитория":   row[2],
								"Комментарий": "",
							}
						}
						delete(classes, "")
					}
					delete(days, "")
				}
			}
		}
		delete(cur, "")
	}

	data = append(data, item)

	// Парсим в JSON
	jsonData, err := json.Marshal(data)
	if err != nil {
		return err
	}

	req, err := http.NewRequest("POST", "http://localhost:8083/update-schedule", bytes.NewBuffer([]byte(jsonData)))
	if err != nil {
		fmt.Println(err)
	}

	// Установка заголовка Content-Type для указания типа данных в запросе
	req.Header.Set("Content-Type", "application/json")

	// Отправка запроса
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Println(err)
	}
	defer resp.Body.Close()

	return nil
}

func convertInterfaceToMap(i interface{}) map[string]interface{} {
	// Проверяем, что интерфейс является типом map
	if m, ok := i.(map[string]interface{}); ok {
		return m
	}
	return nil
}

func valueExists(mymap map[int]string, value string) bool {
	for _, v := range mymap {
		if v == value {
			return true
		}
	}
	return false
}

// Генерация случайного токена запроса доступа при входе в админку через браузер
func generateToken(length int) string {
	// Инициализация генератора случайных чисел
	rand.Seed(time.Now().UnixNano())

	// Допустимые символы для генерации токена
	letters := "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

	// Создание токена заданной длины
	token := make([]byte, length)
	for i := range token {
		token[i] = letters[rand.Intn(len(letters))]
	}

	return string(token)
}
