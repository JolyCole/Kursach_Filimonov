from tkinter import *
import pandas as pd
import random
from datetime import datetime, timedelta

# Списки водителей типов A и B
drivers_A = []
drivers_B = []
drivers_shifts = {}
route_types = ['to the end', 'circular']
shift_duration_A = 8  # Длительность смены для типа A в часах
shift_duration_B = 12  # Длительность смены для типа B в часах
traffic_route_time = 60  # Время маршрута в минутах
start_work_time = '06:00'
end_work_time = '03:00'

def is_weekend(selected_day):
    return selected_day in ['Суббота', 'Воскресенье']

def calculate_route_end(start_time, route_time):
    start_time_obj = datetime.strptime(start_time, "%H:%M")
    end_time_obj = start_time_obj + timedelta(minutes=route_time)
    return end_time_obj.strftime("%H:%M")

def normalize_interval(start_str, end_str):
    start = datetime.strptime(start_str, "%H:%M")
    end = datetime.strptime(end_str, "%H:%M")
    if end < start:
        end += timedelta(days=1)
    return start, end

def is_time_overlap(start_time, end_time, busy_times):
    s, e = normalize_interval(start_time, end_time)
    for (bs, be) in busy_times:
        b_s, b_e = normalize_interval(bs, be)
        if s < b_e and e > b_s:
            return True
    return False

def find_free_slots(driver_busy_times, route_time, break_time):
    free_slots = []
    for driver, periods in driver_busy_times.items():
        normalized = []
        for (st, ft) in periods:
            s_t, f_t = normalize_interval(st, ft)
            normalized.append((s_t, f_t))
        normalized.sort(key=lambda x: x[0])
        current = datetime.strptime("06:00", "%H:%M")
        work_end = datetime.strptime("03:00", "%H:%M") + timedelta(days=1)
        for (st, et) in normalized:
            if (st - current).total_seconds() / 60 >= route_time + break_time:
                free_slots.append((current.strftime("%H:%M"), st.strftime("%H:%M")))
            current = et
        if (work_end - current).total_seconds() / 60 >= route_time + break_time:
            free_slots.append((current.strftime("%H:%M"), work_end.strftime("%H:%M")))
    return free_slots

def calculate_additional_drivers(num_routes, driver_list, shift_duration):
    max_routes_per_driver = int(shift_duration * 60 / traffic_route_time)
    required_drivers = (num_routes + max_routes_per_driver - 1) // max_routes_per_driver
    if len(driver_list) >= required_drivers:
        return 0
    else:
        return required_drivers - len(driver_list)

def can_place_route(candidate_start_time, route_time, driver, driver_busy_times, driver_worked_hours,
                    driver_route_counts, min_break_time):
    candidate_end_time = calculate_route_end(candidate_start_time, route_time)
    if is_time_overlap(candidate_start_time, candidate_end_time, driver_busy_times[driver]):
        return False
    if driver_busy_times[driver]:
        last_start, last_end = driver_busy_times[driver][-1]
        last_end_obj = datetime.strptime(last_end, "%H:%M")
        last_start_obj = datetime.strptime(last_start, "%H:%M")
        if last_end_obj < last_start_obj:
            last_end_obj += timedelta(days=1)
        candidate_start_obj = datetime.strptime(candidate_start_time, "%H:%M")
        if candidate_start_obj < last_end_obj:
            return False
        if (candidate_start_obj - last_end_obj).total_seconds() / 60 < min_break_time:
            return False
    worked_hours = driver_worked_hours[driver]
    if driver in drivers_A and worked_hours >= shift_duration_A:
        return False
    if driver in drivers_B and worked_hours >= shift_duration_B:
        return False
    candidate_end_obj = datetime.strptime(candidate_end_time, "%H:%M")
    if candidate_end_obj < datetime.strptime(candidate_start_time, "%H:%M"):
        candidate_end_obj += timedelta(days=1)
    end_work_obj = datetime.strptime("03:00", "%H:%M") + timedelta(days=1)
    if candidate_end_obj > end_work_obj:
        return False
    return True

def place_route_any_slot(route_time, break_time, min_break_time, driver_list, driver_busy_times, driver_worked_hours,
                         selected_day, driver_route_counts):
    for _ in range(50):
        free_slots = find_free_slots(driver_busy_times, route_time, break_time)
        if not free_slots:
            return None
        slot_start, slot_end = random.choice(free_slots)
        slot_start_obj = datetime.strptime(slot_start, "%H:%M")
        slot_end_obj = datetime.strptime(slot_end, "%H:%M")
        if slot_end_obj < slot_start_obj:
            slot_end_obj += timedelta(days=1)
        max_start = (slot_end_obj - slot_start_obj).total_seconds() / 60 - route_time
        if max_start < 0:
            continue
        offset = random.randint(0, int(max_start))
        candidate_start_obj = slot_start_obj + timedelta(minutes=offset)
        candidate_start = candidate_start_obj.strftime("%H:%M")
        random.shuffle(driver_list)
        for driver in driver_list:
            if driver in drivers_A and is_weekend(selected_day):
                continue
            if can_place_route(candidate_start, route_time, driver, driver_busy_times, driver_worked_hours,
                               driver_route_counts, min_break_time):
                return (driver, candidate_start)
    return None

def try_create_schedule_ga(driver_list, shift_duration, num_routes, selected_day, break_time=10, min_break_time=30):
    available_drivers = list(driver_list)
    random.shuffle(available_drivers)
    driver_busy_times = {driver: [] for driver in available_drivers}
    driver_worked_hours = {driver: 0 for driver in available_drivers}
    driver_route_counts = {driver: 0 for driver in available_drivers}
    schedule = []
    total_routes_assigned = 0
    start_time = datetime.strptime("06:00", "%H:%M")
    end_work_time = datetime.strptime("03:00", "%H:%M") + timedelta(days=1)
    driver_cycle = available_drivers.copy()
    for i in range(num_routes):
        placed = False
        if not driver_cycle:
            driver_cycle = available_drivers.copy()
            random.shuffle(driver_cycle)
        for driver in driver_cycle:
            candidate_start_time = start_time
            candidate_end_time = candidate_start_time + timedelta(minutes=traffic_route_time)
            if candidate_end_time > end_work_time:
                route_type_selected = random.choice(route_types)
                route_type = f"{route_type_selected} (доп рейс)"
            else:
                route_type = random.choice(route_types)
            if can_place_route(candidate_start_time.strftime("%H:%M"), traffic_route_time, driver,
                               driver_busy_times, driver_worked_hours, driver_route_counts, min_break_time):
                schedule.append({
                    'Водитель': driver,
                    'Тип маршрута': route_type,
                    'Время начала': candidate_start_time.strftime("%H:%M"),
                    'Время окончания': candidate_end_time.strftime("%H:%M"),
                    'Маршрутов за смену': driver_route_counts[driver] + 1
                })
                driver_busy_times[driver].append((candidate_start_time.strftime("%H:%M"),
                                                  candidate_end_time.strftime("%H:%M")))
                driver_route_counts[driver] += 1
                driver_worked_hours[driver] += traffic_route_time / 60
                placed = True
                break
        if not placed:
            # Попробовать найти свободный слот для любого водителя
            result = place_route_any_slot(traffic_route_time, break_time, min_break_time, driver_list, driver_busy_times,
                                         driver_worked_hours, selected_day, driver_route_counts)
            if result is None:
                break
            else:
                driver, slot_start = result
                cend = calculate_route_end(slot_start, traffic_route_time)
                cend_obj = datetime.strptime(cend, "%H:%M")
                if cend_obj < datetime.strptime(slot_start, "%H:%M"):
                    cend_obj += timedelta(days=1)
                worked_minutes = (cend_obj - datetime.strptime(slot_start, "%H:%M")).seconds / 60
                final_type = f"{route_type} (доп рейс)"
                schedule.append({
                    'Водитель': driver,
                    'Тип маршрута': final_type,
                    'Время начала': slot_start,
                    'Время окончания': cend,
                    'Маршрутов за смену': driver_route_counts[driver] + 1
                })
                driver_busy_times[driver].append((slot_start, cend))
                driver_route_counts[driver] += 1
                driver_worked_hours[driver] += worked_minutes / 60
        start_time = candidate_end_time + timedelta(minutes=break_time)
        if start_time >= end_work_time:
            start_time = datetime.strptime("06:00", "%H:%M")
            route_type = f"{random.choice(route_types)} (доп рейс)"
    return schedule, len(schedule)

def fitness(schedule, total_drivers):
    num_routes = len(schedule)
    drivers_used = len(set(entry['Водитель'] for entry in schedule))
    # Добавляем вес за каждого задействованного водителя
    return num_routes + drivers_used * 10  # Коэффициент 10 можно настроить

def crossover(parent1, parent2):
    if not parent1 or not parent2:
        return parent1, parent2
    crossover_point = len(parent1) // 2
    child1 = parent1[:crossover_point] + parent2[crossover_point:]
    child2 = parent2[:crossover_point] + parent1[crossover_point:]
    return child1, child2

def mutate(schedule, driver_list, break_time=10):
    if not schedule:
        return schedule
    mutated_schedule = schedule.copy()
    mutation_point = random.randint(0, len(mutated_schedule) - 1)
    new_driver = random.choice(driver_list)
    mutated_schedule[mutation_point]['Водитель'] = new_driver
    if random.random() < 0.5:
        original_start = mutated_schedule[mutation_point]['Время начала']
        original_end = mutated_schedule[mutation_point]['Время окончания']
        start_obj = datetime.strptime(original_start, "%H:%M") + timedelta(minutes=random.randint(-15, 15))
        end_obj = datetime.strptime(original_end, "%H:%M") + timedelta(minutes=random.randint(-15, 15))
        mutated_schedule[mutation_point]['Время начала'] = start_obj.strftime("%H:%M")
        mutated_schedule[mutation_point]['Время окончания'] = end_obj.strftime("%H:%M")
    return mutated_schedule

def display_schedule(result_window, schedule_df, title_text="Итоговое расписание"):
    result_window.title(title_text)
    result_window.configure(bg="black")
    table_frame = Frame(result_window, bg="black")
    table_frame.pack(pady=20, padx=20)
    if not schedule_df.empty:
        cols = list(schedule_df.columns)
        for col, header in enumerate(cols):
            lbl = Label(table_frame, text=header, bg="white", fg="black", font=("Arial", 14, "bold"), bd=1,
                        relief="solid", width=20)
            lbl.grid(row=0, column=col, padx=2, pady=2)
        for i, row in schedule_df.iterrows():
            for col, val in enumerate(row):
                cell = Label(table_frame, text=str(val), bg="white", fg="black", font=("Arial", 12), bd=1,
                             relief="solid", width=20)
                cell.grid(row=i + 1, column=col, padx=2, pady=2)
    else:
        if "Расписание не утверждено" in title_text or "Ошибка" in title_text or "Нет водителей" in title_text:
            message = title_text
        else:
            message = "Не удалось сгенерировать расписание.\nНужно добавить водителей или уменьшить число рейсов."
        lbl = Label(table_frame, text=message, bg="white", fg="red", font=("Arial", 14), wraplength=600,
                    justify=LEFT)
        lbl.pack(pady=20, padx=20)

def generate_optimized_schedule(driver_list, shift_duration, num_routes, selected_day, parent_window, break_time=10,
                                min_break_time=30):
    add_needed = calculate_additional_drivers(num_routes, driver_list, shift_duration)
    if add_needed > 0:
        result_window = Toplevel(parent_window)
        result_window.title("Результат")
        result_window.configure(bg="black")
        display_schedule(result_window, pd.DataFrame(), f"Нехватка сотрудников.\nНужно добавить ещё {add_needed} водителей или уменьшить число рейсов.")
        return
    schedule = []
    driver_busy_times = {d: [] for d in driver_list}
    driver_worked_hours = {d: 0 for d in driver_list}
    driver_route_counts = {d: 0 for d in driver_list}
    current_time = datetime.strptime("06:00", "%H:%M")
    work_end = datetime.strptime("03:00", "%H:%M") + timedelta(days=1)
    for _ in range(num_routes):
        route_type = random.choice(route_types)
        actual_time = traffic_route_time * 2 if route_type == 'circular' else traffic_route_time
        candidate_start_str = current_time.strftime("%H:%M")
        candidate_end_str = calculate_route_end(candidate_start_str, actual_time)
        candidate_end_obj = datetime.strptime(candidate_end_str, "%H:%M")
        if candidate_end_obj < current_time:
            candidate_end_obj += timedelta(days=1)
        if candidate_end_obj > work_end:
            additional_route_type = random.choice(route_types) + " (доп рейс)"
            result = place_route_any_slot(actual_time, break_time, min_break_time, driver_list, driver_busy_times,
                                          driver_worked_hours, selected_day, driver_route_counts)
            if result is None:
                result_window = Toplevel(parent_window)
                result_window.title("Результат")
                result_window.configure(bg="black")
                add_min_needed = calculate_additional_drivers(num_routes, driver_list, shift_duration)
                display_schedule(result_window, pd.DataFrame(), f"Расписание не утверждено.\nНужно добавить сотрудников или уменьшить число рейсов.")
                return
            else:
                driver, slot_start = result
                cend = calculate_route_end(slot_start, actual_time)
                cend_obj = datetime.strptime(cend, "%H:%M")
                if cend_obj < datetime.strptime(slot_start, "%H:%M"):
                    cend_obj += timedelta(days=1)
                worked_minutes = (cend_obj - datetime.strptime(slot_start, "%H:%M")).seconds / 60
                final_type = f"{route_type} (доп рейс)"
                schedule.append({
                    'Водитель': driver,
                    'Тип маршрута': final_type,
                    'Время начала': slot_start,
                    'Время окончания': cend,
                    'Маршрутов за смену': driver_route_counts[driver] + 1
                })
                driver_busy_times[driver].append((slot_start, cend))
                driver_route_counts[driver] += 1
                driver_worked_hours[driver] += worked_minutes / 60
        else:
            placed = False
            copy_drivers = list(driver_list)
            random.shuffle(copy_drivers)
            for driver in copy_drivers:
                if driver in drivers_A and is_weekend(selected_day):
                    continue
                if can_place_route(candidate_start_str, actual_time, driver, driver_busy_times, driver_worked_hours,
                                   driver_route_counts, min_break_time):
                    worked_minutes = (candidate_end_obj - datetime.strptime(candidate_start_str, "%H:%M")).seconds / 60
                    schedule.append({
                        'Водитель': driver,
                        'Тип маршрута': route_type,
                        'Время начала': candidate_start_str,
                        'Время окончания': candidate_end_str,
                        'Маршрутов за смену': driver_route_counts[driver] + 1
                    })
                    driver_busy_times[driver].append((candidate_start_str, candidate_end_str))
                    driver_route_counts[driver] += 1
                    driver_worked_hours[driver] += worked_minutes / 60
                    placed = True
                    break
            if not placed:
                result = place_route_any_slot(actual_time, break_time, min_break_time, driver_list, driver_busy_times,
                                              driver_worked_hours, selected_day, driver_route_counts)
                if result is None:
                    result_window = Toplevel(parent_window)
                    result_window.title("Результат")
                    result_window.configure(bg="black")
                    add_min_needed = calculate_additional_drivers(num_routes, driver_list, shift_duration)
                    display_schedule(result_window, pd.DataFrame(), f"Расписание не утверждено.\nНужно добавить сотрудников или уменьшить число рейсов.")
                    return
                else:
                    driver, slot_start = result
                    cend = calculate_route_end(slot_start, actual_time)
                    cend_obj = datetime.strptime(cend, "%H:%M")
                    if cend_obj < datetime.strptime(slot_start, "%H:%M"):
                        cend_obj += timedelta(days=1)
                    worked_minutes = (cend_obj - datetime.strptime(slot_start, "%H:%M")).seconds / 60
                    final_type = f"{route_type} (доп рейс)"
                    schedule.append({
                        'Водитель': driver,
                        'Тип маршрута': final_type,
                        'Время начала': slot_start,
                        'Время окончания': cend,
                        'Маршрутов за смену': driver_route_counts[driver] + 1
                    })
                    driver_busy_times[driver].append((slot_start, cend))
                    driver_route_counts[driver] += 1
                    driver_worked_hours[driver] += worked_minutes / 60
            current_time = candidate_end_obj + timedelta(minutes=break_time + min_break_time)
        if current_time >= work_end:
            current_time = datetime.strptime("06:00", "%H:%M")
    result_window = Toplevel(parent_window)
    result_window.title("Итоговое расписание")
    result_window.configure(bg="black")
    df = pd.DataFrame(schedule)
    if not df.empty:
        display_schedule(result_window, df, "Итоговое расписание:")
    else:
        display_schedule(result_window, pd.DataFrame(), "Расписание не сформировано.")

def genetic_algorithm_schedule(driver_list, shift_duration, num_routes, selected_day, generations=50,
                               population_size=20, mutation_rate=0.1, break_time=10, min_break_time=30):
    population = []
    total_drivers = len(driver_list)
    for _ in range(population_size):
        schedule, score = try_create_schedule_ga(driver_list, shift_duration, num_routes, selected_day,
                                                 break_time, min_break_time)
        population.append({'schedule': schedule, 'fitness': fitness(schedule, total_drivers)})
    best_schedule = None
    best_fitness = -1
    for gen in range(generations):
        population = sorted(population, key=lambda x: x['fitness'], reverse=True)
        current_best = population[0]
        if current_best['fitness'] > best_fitness:
            best_fitness = current_best['fitness']
            best_schedule = current_best['schedule']
        if best_fitness >= num_routes + total_drivers * 10:
            break
        parents = population[:population_size // 2]
        new_population = parents.copy()
        while len(new_population) < population_size:
            parent1, parent2 = random.sample(parents, 2)
            child1_schedule, child2_schedule = crossover(parent1['schedule'], parent2['schedule'])
            child1 = {'schedule': child1_schedule, 'fitness': fitness(child1_schedule, total_drivers)}
            child2 = {'schedule': child2_schedule, 'fitness': fitness(child2_schedule, total_drivers)}
            new_population.extend([child1, child2])
        for individual in new_population:
            if random.random() < mutation_rate:
                mutated_schedule = mutate(individual['schedule'], driver_list, break_time)
                individual['schedule'] = mutated_schedule
                individual['fitness'] = fitness(mutated_schedule, total_drivers)
        population = new_population[:population_size]
    result_window = Toplevel(root)
    if best_fitness >= num_routes + total_drivers * 10:
        title_text = "Генетический алгоритм завершен. Лучшее расписание"
    else:
        title_text = "Генетический алгоритм завершен. Лучшее найденное расписание"
    if best_schedule and best_fitness > 0:
        df = pd.DataFrame(best_schedule)
        display_schedule(result_window, df, f"{title_text} ({best_fitness} баллов):")
    else:
        display_schedule(result_window, pd.DataFrame(), title_text)

def create_ga_schedule():
    try:
        num_routes = int(num_routes_entry.get())
        day = day_choice.get()
        all_drivers = drivers_A + drivers_B
        shift_duration = max(shift_duration_A, shift_duration_B)
        add_needed = calculate_additional_drivers(num_routes, all_drivers, shift_duration)
        if add_needed > 0:
            result_window = Toplevel(root)
            result_window.title("Результат")
            result_window.configure(bg="black")
            display_schedule(result_window, pd.DataFrame(), f"Недостаточно водителей.\nДобавьте минимум {add_needed} водителей или уменьшите число рейсов.")
            return
        if not drivers_A and not drivers_B:
            result_window = Toplevel(root)
            result_window.title("Результат")
            result_window.configure(bg="black")
            display_schedule(result_window, pd.DataFrame(), "Нет водителей.")
            return
        if is_weekend(day) and not drivers_B:
            result_window = Toplevel(root)
            result_window.title("Результат")
            result_window.configure(bg="black")
            display_schedule(result_window, pd.DataFrame(), "Выходной: Тип A не работает, а типа B нет.")
            return
        if is_weekend(day) and not drivers_A and drivers_B:
            add_need = calculate_additional_drivers(num_routes, drivers_B, shift_duration_B)
            if add_need > 0:
                result_window = Toplevel(root)
                result_window.title("Результат")
                result_window.configure(bg="black")
                display_schedule(result_window, pd.DataFrame(), f"Недостаточно водителей B на выходной. Нужно {add_need}.")
                return
        genetic_algorithm_schedule(all_drivers, shift_duration, num_routes, day,
                                   generations=50, population_size=20, mutation_rate=0.1,
                                   break_time=10, min_break_time=30)
    except ValueError:
        result_window = Toplevel(root)
        result_window.title("Результат")
        result_window.configure(bg="black")
        display_schedule(result_window, pd.DataFrame(), "Не удалось сгенерировать: нужно добавить еще водителей или уменьшить число рейсов ")

def reset_all():
    num_routes_entry.delete(0, END)
    route_time_entry.delete(0, END)
    info_label.config(text="Данные очищены.", fg="white")

def set_route_time():
    global traffic_route_time
    try:
        traffic_route_time = int(route_time_entry.get())
        info_label.config(text="Время маршрута задано.", fg="white")
    except ValueError:
        info_label.config(text="Ошибка: введите число.", fg="white")

def register_driver():
    name = driver_name_entry.get().strip()
    driver_type_val = driver_type.get()
    if not name:
        info_label.config(text="Ошибка: нет имени.", fg="white")
        return
    if driver_type_val == "A":
        drivers_A.append(name)
    else:
        drivers_B.append(name)
    driver_name_entry.delete(0, END)
    info_label.config(text=f"Водитель '{name}' добавлен.", fg="white")

def create_schedule():
    try:
        num_routes = int(num_routes_entry.get())
        day = day_choice.get()
        all_drivers = drivers_A + drivers_B
        if not drivers_A and not drivers_B:
            result_window = Toplevel(root)
            result_window.title("Результат")
            result_window.configure(bg="black")
            display_schedule(result_window, pd.DataFrame(), "Нет водителей.")
            return
        if is_weekend(day) and not drivers_B:
            result_window = Toplevel(root)
            result_window.title("Результат")
            result_window.configure(bg="black")
            display_schedule(result_window, pd.DataFrame(), "Выходной: Тип A не работает, а типа B нет.")
            return
        if is_weekend(day) and not drivers_A and drivers_B:
            add_need = calculate_additional_drivers(num_routes, drivers_B, shift_duration_B)
            if add_need > 0:
                result_window = Toplevel(root)
                result_window.title("Результат")
                result_window.configure(bg="black")
                display_schedule(result_window, pd.DataFrame(), f"Недостаточно водителей B на выходной. Нужно {add_need}.")
                return
            generate_optimized_schedule(drivers_B, shift_duration_B, num_routes, day, root)
            return
        max_shift = max(shift_duration_A, shift_duration_B)
        generate_optimized_schedule(all_drivers, max_shift, num_routes, day, root)
    except ValueError:
        result_window = Toplevel(root)
        result_window.title("Результат")
        result_window.configure(bg="black")
        display_schedule(result_window, pd.DataFrame(), "Не удалось сгенерировать расписание: проверьте установленные данные время в пути и количество рейсов.")

# Инициализация основного окна Tkinter
root = Tk()
root.title("Daily Routes Planner")
root.geometry("1400x600")
root.configure(bg="black")
main_font = ("Arial", 14)
title_font = ("Arial", 20, "bold")
instructions = ("Инструкция:\n"
                "1. Добавьте водителей.\n"
                "2. Установите тип водителя (A или B).\n"
                "3. Укажите количество рейсов на день.\n"
                "4. Задайте время одного рейса (минуты).\n"
                "5. Нажмите 'Утвердить параметры'.\n"
                "6. Сформируйте одно из расписаний.")

# Заголовок приложения
title_label = Label(root, text="Планирование ежедневных рейсов", bg="black", fg="white", font=title_font)
title_label.pack(pady=10)

# Инструкции
instructions_label = Label(root, text=instructions, bg="black", fg="white", font=main_font, justify=LEFT, anchor="w")
instructions_label.pack(pady=10, padx=20, anchor="w")

# Фрейм для ввода данных
input_frame = Frame(root, bg="black")
input_frame.pack(pady=10)

def style_button(btn, text):
    btn.config(text=text, bg="white", fg="black", font=main_font, relief="flat", bd=0, highlightthickness=0, padx=20,
               pady=10)

# Фрейм для ввода имени водителя
driver_frame = Frame(input_frame, bg="black")
driver_frame.grid(row=0, column=0, padx=10)
driver_name_entry = Entry(driver_frame, font=main_font, relief="flat", bg="white", fg="black", width=20)
driver_name_entry.pack()
Label(driver_frame, text="ФИО Сотрудника", bg="black", fg="white", font=("Arial", 10)).pack(pady=2)

# Фрейм для выбора типа водителя
driver_type_frame = Frame(input_frame, bg="black")
driver_type_frame.grid(row=0, column=1, padx=10)
driver_type = StringVar(root)
driver_type.set("A")
driver_type_menu = OptionMenu(driver_type_frame, driver_type, "A", "B")
driver_type_menu.config(font=main_font, relief="flat", bg="white", fg="black", highlightthickness=0, bd=0, width=5)
driver_type_menu.pack()
Label(driver_type_frame, text="Категория водителя", bg="black", fg="white", font=("Arial", 10)).pack(pady=2)

# Фрейм для ввода количества рейсов
routes_frame = Frame(input_frame, bg="black")
routes_frame.grid(row=0, column=2, padx=10)
num_routes_entry = Entry(routes_frame, font=main_font, relief="flat", bg="white", fg="black", width=5)
num_routes_entry.pack()
Label(routes_frame, text="кол-во рейсов на день", bg="black", fg="white", font=("Arial", 10)).pack(pady=2)

# Фрейм для ввода времени маршрута
time_frame = Frame(input_frame, bg="black")
time_frame.grid(row=0, column=3, padx=10)
route_time_entry = Entry(time_frame, font=main_font, relief="flat", bg="white", fg="black", width=5)
route_time_entry.pack()
Label(time_frame, text="время в пути (мин)", bg="black", fg="white", font=("Arial", 10)).pack(pady=2)

# Фрейм для выбора дня недели
day_frame = Frame(input_frame, bg="black")
day_frame.grid(row=0, column=4, padx=10)
day_choice = StringVar(root)
day_choice.set("Понедельник")
day_menu = OptionMenu(day_frame, day_choice, "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота",
                      "Воскресенье")
day_menu.config(font=main_font, relief="flat", bg="white", fg="black", highlightthickness=0, bd=0)
day_menu.pack()
Label(day_frame, text="Укажите день", bg="black", fg="white", font=("Arial", 10)).pack(pady=2)

# Кнопка для добавления водителя
add_driver_button = Button(input_frame, command=register_driver)
style_button(add_driver_button, "Добавить водителя")
add_driver_button.grid(row=0, column=5, padx=10)

# Кнопка для установки времени маршрута
update_time_button = Button(input_frame, command=set_route_time)
style_button(update_time_button, "Утвердить параметры")
update_time_button.grid(row=0, column=6, padx=10)

# Кнопка для очистки всех данных
reset_button = Button(input_frame, command=reset_all)
style_button(reset_button, "Очистить")
reset_button.grid(row=0, column=7, padx=10)

# Нижние кнопки для генерации расписания
bottom_buttons_frame = Frame(root, bg="black")
bottom_buttons_frame.pack(side="bottom", pady=20)
generate_button = Button(bottom_buttons_frame, command=create_schedule)
style_button(generate_button, "Сформировать расписание")
generate_button.pack(side="left", padx=10)
ga_button = Button(bottom_buttons_frame, command=create_ga_schedule)
style_button(ga_button, "Генетическое расписание")
ga_button.pack(side="left", padx=10)

# Метка для отображения информации
info_label = Label(root, text="", bg="black", fg="white", font=main_font)
info_label.pack(pady=10)

# Запуск основного цикла Tkinter
root.mainloop()
