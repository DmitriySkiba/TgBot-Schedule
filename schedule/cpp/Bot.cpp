#include <boost/beast/core.hpp>
#include <boost/beast/http.hpp>
#include <boost/beast/version.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/asio.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/streambuf.hpp>

#include <jwt-cpp/jwt.h>
#include <chrono>
#include <iostream>
#include <fstream>
#include <string>
#include <map>
#include <windows.h>

#include <mongocxx/instance.hpp>
#include <bsoncxx/builder/stream/document.hpp>
#include <bsoncxx/json.hpp>
#include <mongocxx/client.hpp>
#include <windows.h>

#include <bsoncxx/builder/stream/document.hpp>
#include <bsoncxx/json.hpp>
#include <mongocxx/client.hpp>
#include <mongocxx/instance.hpp>
#include <nlohmann/json.hpp>

using json = nlohmann::json;
//#include "json.hpp"
//using json = nlohmann::json;

//json json_struct;

// Загружаем JSON в json_struct
//std::ifstream i("file.json");
//i >> json_struct;

namespace beast = boost::beast;
namespace http = beast::http;
namespace net = boost::asio;
using tcp = net::ip::tcp;

const std::string SCHEDULE_SECRET = "5678";

// Проверка недели на четность
bool isWeekEven() {
    // Получение текущей даты и времени
    auto now = std::chrono::system_clock::now();
    std::time_t currentTime = std::chrono::system_clock::to_time_t(now);

    // Преобразование текущей даты и времени в структуру tm
    std::tm* timeinfo = std::localtime(&currentTime);


    // Получение номера недели в году
    int weekNumber = timeinfo->tm_yday / 7;

    // Проверка чётности недели
    if (weekNumber % 2 == 0) {
        return true;  // Неделя чётная
    }
    else {
        return false; // Неделя нечётная
    }
}

// Расписание на сегодня
std::string get_today(json doc, std::string group) {
    std::string week;
    if (isWeekEven()) {
        week = u8"Четная неделя";
    }
    else {
        week = u8"Нечетная неделя";
    }

    time_t now = time(nullptr);

    // Преобразуем текущую дату и время в структуру tm
    struct tm* tm = localtime(&now);

    // Получаем день недели
    int day = tm->tm_wday;
    std::string day_name;

    if (day == 1) {
        day_name = u8"ПН";
    }
    else if (day == 2) {
        day_name = u8"ВТ";
    }
    else if (day == 3) {
        day_name = u8"СР";
    }
    else if (day == 4) {
        day_name = u8"ЧТ";
    }
    else if (day == 5) {
        day_name = u8"ПТ";
    }
    else if (day == 6) {
        day_name = u8"СБ";
    }
    else if (day == 7) {
        day_name = u8"ВС";
    }

    std::string response1, response2, response3, response4, response5, response;
    if (day_name != "СБ" && day_name != "ВС") {
        response1 = "1." + doc[week][group][day_name]["1"][u8"Предмет"].dump();
        response2 = "2." + doc[week][group][day_name]["2"][u8"Предмет"].dump();
        response3 = "3." + doc[week][group][day_name]["3"][u8"Предмет"].dump();
        response4 = "4." + doc[week][group][day_name]["4"][u8"Предмет"].dump();
        response5 = "5." + doc[week][group][day_name]["5"][u8"Предмет"].dump();
        response = response1 + "\n" + response2 + "\n" + response3 + "\n" + response4 + "\n" + response5;
    }
    else {
        response = "Выходной";
    }

    return response;
}

// Расписание на завтра
std::string get_tomorrow(json doc, std::string group) {
    std::string week;
    if (isWeekEven()) {
        week = u8"Четная неделя";
    }
    else {
        week = u8"Нечетная неделя";
    }

    time_t now = time(nullptr);

    // Преобразуем текущую дату и время в структуру tm
    struct tm* tm = localtime(&now);

    // Получаем день недели
    int day = tm->tm_wday;
    std::string day_name;

    if (day == 1) {
        day_name = u8"ВТ";
    }
    else if (day == 2) {
        day_name = u8"СР";
    }
    else if (day == 3) {
        day_name = u8"ЧТ";
    }
    else if (day == 4) {
        day_name = u8"ПТ";
    }
    else if (day == 5) {
        day_name = u8"СБ";
    }
    else if (day == 6) {
        day_name = u8"ВС";
    }
    else if (day == 7) {
        day_name = u8"ПН";
    }

    std::string response1, response2, response3, response4, response5, response;
    if (day_name != "ПТ" && day_name != "СБ") {
        response1 = "1." + doc[week][group][day_name]["1"][u8"Предмет"].dump();
        response2 = "2." + doc[week][group][day_name]["2"][u8"Предмет"].dump();
        response3 = "3." + doc[week][group][day_name]["3"][u8"Предмет"].dump();
        response4 = "4." + doc[week][group][day_name]["4"][u8"Предмет"].dump();
        response5 = "5." + doc[week][group][day_name]["5"][u8"Предмет"].dump();
        response = response1 + "\n" + response2 + "\n" + response3 + "\n" + response4 + "\n" + response5;
    }
    else {
        response = "Выходной";
    }

    return response;
}

// Расписания по дням недели
std::string get_week_day(json doc, std::string group, std::string action) {

    std::string n;

    if (action == "monday") {
        n = u8"ПН";
    }
    else if (action == "tuesday") {
        n = u8"ВТ";
    }
    else if (action == "wednesday") {
        n = u8"СР";
    }
    else if (action == "thursday") {
        n = u8"ЧТ";
    }
    else if (action == "friday") {
        n = u8"ПТ";
    }

    std::string response1, response2, response3, response4, response5, response;
    std::string response6, response7, response8, response9, response10;
    response1 = "1." + doc[u8"Нечетная неделя"][group][n]["1"][u8"Предмет"].dump();
    response2 = "2." + doc[u8"Нечетная неделя"][group][n]["2"][u8"Предмет"].dump();
    response3 = "3." + doc[u8"Нечетная неделя"][group][n]["3"][u8"Предмет"].dump();
    response4 = "4." + doc[u8"Нечетная неделя"][group][n]["4"][u8"Предмет"].dump();
    response5 = "5." + doc[u8"Нечетная неделя"][group][n]["5"][u8"Предмет"].dump();

    response6 = "1." + doc[u8"Четная неделя"][group][n]["1"][u8"Предмет"].dump();
    response7 = "2." + doc[u8"Четная неделя"][group][n]["2"][u8"Предмет"].dump();
    response8 = "3." + doc[u8"Четная неделя"][group][n]["3"][u8"Предмет"].dump();
    response9 = "4." + doc[u8"Четная неделя"][group][n]["4"][u8"Предмет"].dump();
    response10 = "5." + doc[u8"Четная неделя"][group][n]["5"][u8"Предмет"].dump();

    response = u8"Нечетная неделя:\n" + response1 + "\n" + response2 + "\n" + response3 + "\n" + response4 + "\n" + response5 + "\n\n" + u8"Четная неделя:\n" + response6 + "\n" + response7 + "\n" + response8 + "\n" + response9 + "\n" + response10;

    return response;
}

// Следующая пара
std::string get_next_lesson(json doc, std::string group) {

    std::string response;
    std::string week;

    if (isWeekEven()) {
        week = u8"Четная неделя";
    } else {
        week = u8"Нечетная неделя";
    }

    auto current_time = std::chrono::system_clock::now();
    std::time_t nowTime = std::chrono::system_clock::to_time_t(current_time);

    struct std::tm* nowTM = std::localtime(&nowTime);

    int currentHour = nowTM->tm_hour;
    int currentminute = nowTM->tm_min;

    std::string lesson_time = "0";
    if ((currentHour == 8 && currentminute >= 0) || (currentHour == 11 && currentminute <= 30)) {
        lesson_time = "3";
    }
    else if ((currentHour == 11 && currentminute >= 30) || (currentHour == 15 && currentminute == 00)) {
        lesson_time = "5";
    }
    else {
        lesson_time = "---";
    }

    time_t now = time(nullptr);

    // Преобразуем текущую дату и время в структуру tm
    struct tm* tm = localtime(&now);

    // Получаем день недели
    int day_of_week = tm->tm_wday;
    std::string day_week;

    if (day_of_week == 1) {
        day_week == u8"ПН";
    }
    else if (day_of_week == 2) {
        day_week == u8"ВТ";
    }
    else if (day_of_week == 3) {
        day_week == u8"СР";
    }
    else if (day_of_week == 4) {
        day_week == u8"ЧТ";
    }
    else if (day_of_week == 5) {
        day_week == u8"ПТ";
    }
    else {
        day_week == "---";
    }


    if (lesson_time != "---" && day_week != "---") {
        response = doc[week][group][day_week][lesson_time][u8"Предмет"].dump() + " " + doc[week][group][day_week][lesson_time][u8"Аудитория"].dump();
    }
    else {
        response = "Занятия закончились";
    }

    return response;
}




// Обработчик запросов
void handleRequest(tcp::socket& socket) {

    beast::flat_buffer buffer;
    http::request<http::string_body> request;
    http::read(socket, buffer, request);

    // Обновление расписания, полученного из админки ===============================/
    if (request.target() == "/update-schedule") {

        mongocxx::client conn{ mongocxx::uri{"mongodb+srv://Vladimir:pazintrul@tgbot.rnldbuj.mongodb.net/?retryWrites=true&w=majority"} };

        // Преобразование JSON-строки в документ BSON
        bsoncxx::document::value doc = bsoncxx::from_json(request.body());

        auto collection = conn["TGbot"]["schedule"];

        // Заменяем расписание на новое
        collection.delete_many({});
        collection.insert_one(doc.view());

        // Отправка ответного сообщения
        http::response<http::string_body> response(http::status::ok, request.version());
        response.set(http::field::server, BOOST_BEAST_VERSION_STRING);
        response.set(http::field::content_type, "text/plain");
        response.body() = "Расписание успешно обновлено\n";
        response.prepare_payload();

        http::write(socket, response);
    } 

    // Вывод информации о расписании в бота ========================================/
    else if (request.target() == "/get-schedule") {

        // Извлечение данных из запроса ------------------------/
        std::unordered_map<std::string, std::string> postData;
        std::string body = request.body();

        std::size_t currentPosition = 0;
        while (currentPosition < body.size())
        {
            std::size_t delimiterPosition = body.find('&', currentPosition);
            if (delimiterPosition == std::string::npos)
                delimiterPosition = body.size();

            std::size_t equalsPosition = body.find('=', currentPosition);
            if (equalsPosition == std::string::npos || equalsPosition > delimiterPosition)
            {
                currentPosition = delimiterPosition + 1;
                continue;
            }

            std::string key = body.substr(currentPosition, equalsPosition - currentPosition);
            std::string value = body.substr(equalsPosition + 1, delimiterPosition - equalsPosition - 1);

            postData[key] = value;
            currentPosition = delimiterPosition + 1;
        }
        // -----------------------------------------------------/

        std::string token = postData["token"];
        auto decoded_token = jwt::decode(token);

        // Выполняем проверку подписи токена ключом SECRET
        try {
            // Создаём проверяющий объект
            auto verifier = jwt::verify().allow_algorithm(jwt::algorithm::hs256{ SCHEDULE_SECRET });
            // Проверяем
            verifier.verify(decoded_token);

            // Если токен валидный, проходим дальше, иначе попадаем в catch
            auto payload = decoded_token.get_payload_claims();

            std::time_t expiration_time = payload["expires_at"].as_int();
            std::time_t current_time = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
            

            // Ответ боту в виде текста
            std::string textToSend = "";

            // Проверяем, не устарел ли токен, и соответствие типа действия
            if (current_time < expiration_time && payload["action"].as_string() == postData["action"]) {
                // Достаем расписание из MongoDB
                mongocxx::client conn{ mongocxx::uri{"mongodb+srv://Vladimir:pazintrul@tgbot.rnldbuj.mongodb.net/?retryWrites=true&w=majority"} };

                auto collection = conn["TGbot"]["schedule"];
                bsoncxx::stdx::optional<bsoncxx::document::value> result = collection.find_one({});

                json doc = json::parse(bsoncxx::to_json(*result));

                std::string action = postData["action"];

                // Где следующая пара?
                if (action == "where_next_class") {
                    textToSend = get_next_lesson(doc["0"], u8"ПИ-б-о 232(2)");
                }
                // Где преподаватель?
                else if (action == "where_teacher") {

                }
                // Когда экзамен?
                else if (action == "when_exam") {
                    textToSend = "Точные даты экзаменов появятся позже";
                }
                // Расписание на сегодня
                else if (action == "today") {
                    textToSend = get_today(doc["0"], u8"ПИ-б-о 232(2)");
                }
                // Расписание на завтра
                else if (action == "tomorrow") {
                    textToSend = get_tomorrow(doc["0"], u8"ПИ-б-о 232(2)");
                }
                // Расписание по дням недели
                else {
                    textToSend = get_week_day(doc["0"], u8"ПИ-б-о 232(2)", action);
                }

                std::cout << textToSend << std::endl;

                // Отправка ответного сообщения
                http::response<http::string_body> response(http::status::ok, request.version());
                response.set(http::field::server, BOOST_BEAST_VERSION_STRING);
                response.set(http::field::content_type, u8"Content-Type: text/plain; charset=utf-8");
                response.body() = textToSend;
                response.prepare_payload();

                http::write(socket, response);

            } else {
                std::cout << "JWT токен истек или тип действия не совпадает" << std::endl;
            }

        }
        catch (...) {
            std::cout << "INVALID TOKEN OR ERROR GETTING DATA " << std::endl;
        }

    } 

    // Отправка кода ошибки 404 Not Found
    else {
        http::response<http::string_body> response(http::status::not_found, request.version());
        response.set(http::field::server, BOOST_BEAST_VERSION_STRING);
        response.set(http::field::content_type, "text/plain");
        response.body() = "404 Not Found";
        response.prepare_payload();

        http::write(socket, response);
    }
    
}

int main() {
    SetConsoleOutputCP(65001);

    mongocxx::instance inst{};


    // Для теста
    //mongocxx::client conn{ mongocxx::uri{"mongodb+srv://Vladimir:pazintrul@tgbot.rnldbuj.mongodb.net/?retryWrites=true&w=majority"} };

    //auto collection = conn["TGbot"]["schedule"];
    //bsoncxx::stdx::optional<bsoncxx::document::value> result = collection.find_one({});

    //json doc = json::parse(bsoncxx::to_json(*result));

    //std::string res = get_next_lesson(doc["0"], u8"ПИ-б-о 232(2)");

    //std::cout << res << std::endl;



    try {
        net::io_context io_context;
        tcp::acceptor acceptor(io_context, tcp::endpoint(tcp::v4(), 8083));

        std::cout << "Server started..." << std::endl;

        while (true) {
            tcp::socket socket(io_context);
            acceptor.accept(socket);
            handleRequest(socket);
        }

    } catch (const std::exception& e) {
        std::cerr << "Ошибка: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
