import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import requests
import mysql.connector
import webbrowser
from tkcalendar import DateEntry
from datetime import datetime, date
import csv
from tkinter import filedialog, messagebox
import os
from dotenv import load_dotenv


load_dotenv()  # încarcă variabilele din .env

API_KEY = os.getenv("API_KEY") # api-key cheia api importata din .env

if not API_KEY:
    raise RuntimeError("API KEY lipsă! Verifică fișierul .env")

ADMIN_PASSWORD = "aici pui parola admin cand stergi clienti din baza de date"  # parolă pentru ștergere client din baza de date


# =========================
# CĂUTARE FIRMĂ ÎN API dupa cod fiscal
# =========================
def cauta_firma_firmeapi(cui):
    cui = cui.strip().replace("RO", "").replace("ro", "")
    url = f"https://www.firmeapi.ro/api/v1/firma/{cui}"
    headers = {"X-API-KEY": API_KEY, "Accept": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except requests.RequestException:
        return None
    firma = r.json().get("data")
    if not firma:
        return None
    adresa_completa = ""
    sediu = firma.get("adresa_sediu_social", {})
    if isinstance(sediu, dict):
        strada = sediu.get("strada", "")
        numar = sediu.get("numar", "")
        localitate = ""
        judet = ""
        if isinstance(sediu.get("localitate"), dict):
            local = sediu["localitate"]
            localitate = local.get("nume", "")
            judet = local.get("judet", {}).get("nume", "")
        elif isinstance(sediu.get("localitate"), str):
            localitate = sediu.get("localitate")
        adresa_completa = f"{strada} {numar}, {localitate}, {judet}".strip(" ,")
    return {
        "cui": firma.get("cui", cui),
        "nume": firma.get("denumire", ""),
        "adresa": adresa_completa,
        "reg_comert": firma.get("nr_reg_com", "")
    }


# =========================
# FUNCȚII CRUD
# =========================
def conectare_db():
    return mysql.connector.connect(host="localhost", user="root", password="cipri", database="date_clienti")


def incarca_dropdown_puncte():
    for i in tree.get_children():
        tree.delete(i)
    conn = conectare_db()
    cursor = conn.cursor()
    cursor.execute("""SELECT d.Nr_Crt, d.Nume_Firma, d.Cui, d.Sediu_Social,
                      s.Punct_Lucru, s.Model_Amef, s.Serie_Amef
                      FROM tabela_date_clienti d
                      LEFT JOIN tabela_sedii_secundare s ON d.Nr_Crt = s.Id_Client""")
    for row in cursor.fetchall():
        tree.insert("", "end", values=row)
    conn.close()


# Functie pentru golirea tuturor campurilor din interfata
def resetare_toate_campurile():
    for e in entries.values():
        e.delete(0, tk.END)


# functie de resetare a campului de cautare client
def resetare_camp_cautare():
    search_entry.delete(0, tk.END)
    for item in tree.get_children():
        tree.delete(item)


# Funtie pentru modificarea datelor introduse gresit
"""Populează câmpurile cu datele clientului după CUI și punct de lucru pentru editare"""


def modifica_date_client():
    cui = entry_cui.get().strip()
    serie_amef = entry_serie_amef.get().strip()

    if not cui:
        messagebox.showwarning("Eroare", "Introduceți CUI-ul clientului")
        return

    conn = conectare_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
            SELECT d.Nume_Firma, d.Cui, d.Reg_Comert, d.Tva, d.Sediu_Social,
                   s.Punct_Lucru, s.Model_Amef, s.Serie_Amef, s.Nui,
                   s.Tehnician, s.Data_Conect_Anaf, s.Data_Exp_Abon, s.Val_Ctr, s.Nr_Ctr
            FROM tabela_date_clienti d
            LEFT JOIN tabela_sedii_secundare s ON d.Nr_Crt = s.Id_Client
            WHERE d.Cui=%s AND s.Serie_Amef=%s
        """, (cui, serie_amef))
    result = cursor.fetchone()
    conn.close()

    if not result:
        messagebox.showinfo("Info", "Nu s-a găsit clientul sau punctul de lucru")
        return

    # Populare câmpuri
    mapping = {
        "Nume firmă": result["Nume_Firma"],
        "CUI Client": result["Cui"],
        "Nr. Registrul Comertului": result["Reg_Comert"],
        "Plătitor TVA": result["Tva"],
        "Adresă sediu": result["Sediu_Social"],
        "Punct de lucru": result["Punct_Lucru"],
        "Model Amef": result["Model_Amef"],
        "Serie Amef": result["Serie_Amef"],
        "Nui Amef": result["Nui"],
        "Tehnician Service": result["Tehnician"],
        "Data conectare Anaf": result["Data_Conect_Anaf"],
        "Data expirare abonament": result["Data_Exp_Abon"],
        "Valoare contract - RON": result["Val_Ctr"],
        "Numar Contract": result["Nr_Ctr"]
    }

    for label, value in mapping.items():
        entries[label].delete(0, tk.END)
        entries[label].insert(0, value)


def cauta_firma():
    cui = entry_cui.get().strip()
    if not cui:
        messagebox.showwarning("Eroare", "Introduceți un CUI")
        return
    info = cauta_firma_firmeapi(cui)
    if not info:
        messagebox.showinfo("Info", "Firma nu a fost găsită")
        return
    entry_nume.delete(0, tk.END)
    entry_nume.insert(0, info["nume"])
    entry_adresa.delete(0, tk.END)
    entry_adresa.insert(0, info["adresa"])
    entry_reg_comert.delete(0, tk.END)
    entry_reg_comert.insert(0, info["reg_comert"])


def salveaza_client():
    data = {
        "cui": entry_cui.get().strip(),
        "nume": entry_nume.get().strip(),
        "adresa": entry_adresa.get().strip(),
        "reg_comert": entry_reg_comert.get().strip(),
        "tva": entry_tva.get().strip(),
        "administrator": entry_administrator.get().strip(),
        "status_firma": entry_status_firma.get().strip(),
        "telefon": entry_telefon.get().strip(),
        "mail": entry_mail.get().strip(),
        "punct_lucru": entry_punct_lucru.get().strip(),
        "model_amef": entry_model_amef.get().strip(),
        "serie_amef": entry_serie_amef.get().strip(),
        "nui": entry_nui.get().strip(),
        "tip_abonament": entry_tip_abonament.get().strip(),
        "data_conect": entry_conectare_anaf.get().strip(),
        "tehnician": entry_tehnician.get().strip(),
        "data_exp": entry_data_exp.get().strip(),
        "val_ctr": entry_val_ctr.get().strip(),
        "nr_ctr": entry_nr_ctr.get().strip()
    }

    if not data["cui"] or not data["nume"]:
        messagebox.showwarning("Eroare", "CUI și Nume Firmă sunt obligatorii!")
        return

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="aici pui parola de la baza de date mysql",
        database="date_clienti"
    )
    cursor = conn.cursor()

    # verific client existent
    cursor.execute("SELECT Nr_Crt FROM tabela_date_clienti WHERE Cui=%s OR Reg_Comert=%s",
                   (data["cui"], data["reg_comert"]))
    result = cursor.fetchone()

    if result:
        id_client = result[0]
        cursor.execute("""
            UPDATE tabela_date_clienti
            SET Nume_Firma=%s, Sediu_Social=%s, Tva=%s, Administrator=%s,
                Status_Firma=%s, Nr_Telefon=%s, Mail=%s
            WHERE Nr_Crt=%s
        """, (
            data["nume"], data["adresa"], data["tva"], data["administrator"],
            data["status_firma"], data["telefon"], data["mail"], id_client
        ))
        messagebox.showinfo("Info", f"Client existent. Datele au fost actualizate (Nr_Crt={id_client})")
    else:
        cursor.execute("""
            INSERT INTO tabela_date_clienti
            (Nume_Firma, Sediu_Social, Cui, Nr_Telefon, Mail, Reg_Comert, Tva, Administrator, Status_Firma)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data["nume"], data["adresa"], data["cui"], data["telefon"], data["mail"],
            data["reg_comert"], data["tva"], data["administrator"], data["status_firma"]
        ))
        id_client = cursor.lastrowid
        messagebox.showinfo("Succes", f"Client nou adăugat (Nr_Crt={id_client})")

    # punct de lucru
    cursor.execute("SELECT 1 FROM tabela_sedii_secundare WHERE Id_Client=%s AND Serie_Amef=%s",
                   (id_client, data["serie_amef"]))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE tabela_sedii_secundare
            SET Punct_Lucru=%s, Model_Amef=%s, Nui=%s, Tip_Abonament=%s,
                Data_Conect_Anaf=%s, Tehnician=%s, Data_Exp_Abon=%s,
                Val_Ctr=%s, Nr_Ctr=%s
            WHERE Id_Client=%s AND Serie_Amef=%s
        """, (
            data["punct_lucru"], data["model_amef"], data["nui"], data["tip_abonament"],
            data["data_conect"], data["tehnician"], data["data_exp"],
            data["val_ctr"], data["nr_ctr"], id_client, data["serie_amef"]
        ))
        messagebox.showinfo("Succes", f"Punct de lucru {data['serie_amef']} actualizat")
    else:
        cursor.execute("""
            INSERT INTO tabela_sedii_secundare
            (Id_Client, Punct_Lucru, Model_Amef, Serie_Amef, Nui,
             Tip_Abonament, Data_Conect_Anaf, Tehnician, Data_Exp_Abon, Val_Ctr, Nr_Ctr)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            id_client, data["punct_lucru"], data["model_amef"], data["serie_amef"], data["nui"],
            data["tip_abonament"], data["data_conect"], data["tehnician"],
            data["data_exp"], data["val_ctr"], data["nr_ctr"]
        ))
        messagebox.showinfo("Succes", f"Punct de lucru {data['serie_amef']} adăugat")

    conn.commit()
    conn.close()


def sterge_client():
    parola = simpledialog.askstring("Parola Admin", "Introduceți parola pentru ștergere:", show="*")
    if parola != ADMIN_PASSWORD:
        messagebox.showerror("Eroare", "Parola incorectă!")
        return
    cui = entry_cui.get().strip()
    if not cui:
        messagebox.showwarning("Eroare", "Introduceți CUI-ul clientului")
        return
    if not messagebox.askyesno("Confirmare", f"Sigur doriți să ștergeți clientul {cui} și toate punctele sale?"):
        return
    conn = conectare_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Nr_Crt FROM tabela_date_clienti WHERE Cui=%s", (cui,))
    result = cursor.fetchone()
    if not result:
        messagebox.showinfo("Info", "Clientul nu există")
        conn.close()
        return
    id_client = result[0]
    cursor.execute("DELETE FROM tabela_sedii_secundare WHERE Id_Client=%s", (id_client,))
    cursor.execute("DELETE FROM tabela_date_clienti WHERE Nr_Crt=%s", (id_client,))
    conn.commit()
    conn.close()
    messagebox.showinfo("Succes", f"Client {cui} și punctele sale au fost șterse")
    resetare_toate_campurile()
    incarca_dropdown_puncte()


def sterge_punct():
    parola = simpledialog.askstring("Parola Admin", "Introduceți parola pentru ștergere:", show="*")
    if parola != ADMIN_PASSWORD:
        messagebox.showerror("Eroare", "Parola incorectă!")
        return
    serie_amef = entry_serie_amef.get().strip()
    if not serie_amef:
        messagebox.showwarning("Eroare", "Introduceți seria AMEF a punctului")
        return
    if not messagebox.askyesno("Confirmare", f"Sigur doriți să ștergeți punctul {serie_amef}?"):
        return
    conn = conectare_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tabela_sedii_secundare WHERE Serie_Amef=%s", (serie_amef,))
    conn.commit()
    conn.close()
    messagebox.showinfo("Succes", f"Punct {serie_amef} a fost șters")
    resetare_toate_campurile()
    incarca_dropdown_puncte()


def cauta_in_treeview():
    query = search_entry.get().strip().lower()

    # Curățare Treeview
    for item in tree.get_children():
        tree.delete(item)

    conn = conectare_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            d.Nr_Crt,
            d.Nume_Firma,
            d.Cui,
            d.Sediu_Social,
            d.Nr_Telefon,
            d.Mail,
            d.Reg_Comert,
            d.Tva,
            d.Administrator,
            d.Status_Firma,
            s.Punct_Lucru,
            s.Model_Amef,
            s.Serie_Amef,
            s.Nui,
            s.Tehnician,
            s.Data_Conect_Anaf,
            s.Data_Exp_Abon,
            s.Val_Ctr,
            s.Tip_Abonament,
            s.Nr_Ctr

        FROM tabela_date_clienti d
        LEFT JOIN tabela_sedii_secundare s ON d.Nr_Crt = s.Id_Client
    """)

    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        if (
                query in str(row["Nume_Firma"]).lower()
                or query in str(row["Cui"]).lower()
        ):
            tag = calculeaza_tag_abonament(row["Data_Exp_Abon"])
            tree.insert("", "end", values=(
                row["Nr_Crt"],
                row["Nume_Firma"],
                row["Cui"],
                row["Sediu_Social"],
                row["Nr_Telefon"],
                row["Mail"],
                row["Reg_Comert"],
                row["Tva"],
                row["Administrator"],
                row["Status_Firma"],
                row["Punct_Lucru"],
                row["Model_Amef"],
                row["Serie_Amef"],
                row["Nui"],
                row["Tehnician"],
                row["Data_Conect_Anaf"],
                row["Data_Exp_Abon"],
                row["Val_Ctr"],
                row["Tip_Abonament"],
                row["Nr_Ctr"],

            ),
                        tags=(tag,)
                        )


# =========================
# Functia care populeaza campurile de date din cele 2 coloane date client si sediu/amef
# =========================
def populare_campuri_treeview(event):
    selected = tree.focus()
    if not selected:
        return

    values = tree.item(selected, "values")

    mapping = {
        # date client
        "CUI Client": values[2],  # Cod Fiscal
        "Nume firmă": values[1],  # Nume Firma
        "Adresă sediu": values[3],  # Sediu Social
        "Numar Telefon": values[4],  # Nr Telefon
        "Adresa mail": values[5],  # Mail
        "Registrul Comertului": values[6],  # Reg Comert
        "Plătitor TVA": values[7],  # Tva
        "Administrator Firma": values[8],  # Administrator
        "Status Firma": values[9],  # Statusul Firmei Activ/Inchis

        # sediu secundar
        "Punct de lucru": values[10],  # Punct Lucru
        "Model Amef": values[11],  # Model AMEF
        "Serie Amef": values[12],  # Serie AMEF
        "Nui Amef": values[13],  # NUI
        "Tehnician Service": values[14],  # Tehnician srv
        "Data conectare Anaf": values[15],  # Data Conectare Anaf
        "Data expirare abonament": values[16],  # Data Exp. Abonament
        "Valoare contract - RON": values[17],  # Val_Ctr
        "Tip Abonament": values[18],  # Tip Abonament
        "Numar Contract": values[19],  # Nr_Ctr
    }

    for label, val in mapping.items():
        if label in entries:
            entries[label].delete(0, tk.END)
            entries[label].insert(0, val)


# Functie pentru a modifica tehnicianul de service
def modifica_tehnician():
    serie_amef = entry_serie_amef.get().strip()
    tehnician_nou = entry_tehnician.get().strip()

    if not serie_amef:
        messagebox.showwarning("Eroare", "Trebuie să introduci seria AMEF pentru a identifica punctul de lucru")
        return

    if not tehnician_nou:
        messagebox.showwarning("Eroare", "Trebuie să introduci numele tehnicianului")
        return

    # conectare la baza de date
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="aici pui parola de la baza de date mysql",
        database="date_clienti"
    )
    cursor = conn.cursor()

    try:
        # verificam daca exista punctul de lucru cu seria AMEF introdusa
        cursor.execute("""
        SELECT Id_Client, Punct_Lucru FROM tabela_sedii_secundare WHERE Serie_Amef=%s
        """, (serie_amef,))
        result = cursor.fetchone()

        if not result:
            messagebox.showinfo("Info", "Nu există niciun punct de lucru cu această serie AMEF")
            return

        id_client, punct_lucru = result

        # actualizare doar a tehnicianului pentru punctul de lucru respectiv
        cursor.execute("""
        UPDATE tabela_sedii_secundare
        SET Tehnician=%s
        WHERE Id_Client=%s AND Serie_Amef=%s
        """, (tehnician_nou, id_client, serie_amef))

        conn.commit()
        messagebox.showinfo("Succes", f"Numele tehnicianului a fost modificat pentru seria AMEF {serie_amef}!")

    except mysql.connector.Error as e:
        messagebox.showerror("Eroare", f"Nu s-a putut modifica tehnicianul: {e}")
    finally:
        conn.close()

# Functie pentru calcularea valabilitatiii abonamentului
def calculeaza_tag_abonament(data_exp):
    if not data_exp:
        return "expirat"

    # Dacă vine deja ca date (din MySQL)
    if isinstance(data_exp,date):
        data_exp_date = data_exp
    else:
        try:
            # acceptă: YYYY-MM-DD sau YYYY-MM-DD HH:MM:SS
            data_exp_date = datetime.fromisoformat(str(data_exp)).date()
        except ValueError:
            return "expirat"

    azi = date.today()
    zile_ramase = (data_exp_date - azi).days

    if zile_ramase < 0:
        return "expirat"
    elif zile_ramase <= 20:
        return "avertizare"
    else:
        return "valid"

# Functie de alertare expirare abonament
def alerta_abonamente_color():
    conn = conectare_db()
    cursor = conn.cursor(dictionary=True)

    azi = date.today()
    luna_curenta = azi.month
    anul_curent = azi.year

    cursor.execute("""
        SELECT d.Nume_Firma, d.Cui, s.Serie_Amef, s.Data_Exp_Abon
        FROM tabela_date_clienti d
        LEFT JOIN tabela_sedii_secundare s ON d.Nr_Crt = s.Id_Client
    """)

    rows = cursor.fetchall()
    conn.close()

    # Cream fereastra pop-up
    popup = tk.Toplevel()
    popup.title("Alertă Abonamente")
    popup.geometry("700x400")

    # Scrollbar
    canvas = tk.Canvas(popup)
    scrollbar = tk.Scrollbar(popup, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas)

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Adăugăm label-uri colorate
    for r in rows:
        data_exp = r["Data_Exp_Abon"]
        if not data_exp:
            continue

        # Convertim string la date dacă e necesar
        if isinstance(data_exp, str):
            try:
                data_exp = datetime.fromisoformat(data_exp).date()
            except ValueError:
                continue
        # Aici calculam zilele ramase pana la expirarea abonamentului
        zile_ramase = (data_exp - azi).days

        # aici calculam zilele ramase pana la expirare
        if zile_ramase < 0:
            text_status = "Expirat"
            culoare = "#f28c8c"  # roșu
        elif data_exp.month == luna_curenta and data_exp.year == anul_curent:
            text_status = f"Expiră în {zile_ramase} zile"
            culoare = "#fff3b0"  # galben
        else:
            continue  # ignoră abonamentele valabile mai departe

        text = f"{r['Nume_Firma']} (CUI: {r['Cui']}) - Seria: {r['Serie_Amef']} - Data expirării: {data_exp} - {text_status}"

        # text = f"{r['Nume_Firma']} (CUI: {r['Cui']}) - Seria: {r['Serie_Amef']} - Expiră: {data_exp}"

        # if zile_ramase < 0:
        #     culoare = "#f28c8c"  # roșu = expirat
        # elif data_exp.month == luna_curenta and data_exp.year == anul_curent:
        #     culoare = "#fff3b0"  # galben = expira luna asta
        # else:
        #     continue  # ignoră abonamentele valabile mai departe

        lbl = tk.Label(scroll_frame, text=text, bg=culoare, anchor="w", justify="left", font=("Arial", 10))
        lbl.pack(fill="x", padx=5, pady=2)

# Functie pentru export baza date in format CSV
def export_csv():
    conn = conectare_db()
    cursor = conn.cursor()

    # export tabela_date_clienti
    cursor.execute("SELECT * FROM tabela_date_clienti")
    clienti = cursor.fetchall()
    clienti_headers = [i[0] for i in cursor.description]

    # export tabela_sedii_secundare
    cursor.execute("SELECT * FROM tabela_sedii_secundare")
    sedii = cursor.fetchall()
    sedii_headers = [i[0] for i in cursor.description]

    conn.close()

    # alegem folder și nume fișier
    file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV files", "*.csv")],
                                             title="Export Bază de Date")
    if not file_path:
        return

    # salvăm tabela_date_clienti
    with open(file_path.replace(".csv", "_clienti.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(clienti_headers)
        writer.writerows(clienti)

    # salvăm tabela_sedii_secundare
    with open(file_path.replace(".csv", "_sedii.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(sedii_headers)
        writer.writerows(sedii)

    messagebox.showinfo("Succes", f"Baza de date a fost exportată:\n{file_path}_clienti.csv și {file_path}_sedii.csv")

# Functie importarea bazei de date in Format CSV
def import_csv():
    # alegem fișierele CSV
    file_clienti = filedialog.askopenfilename(title="Selectează CSV tabela_date_clienti",
                                              filetypes=[("CSV files", "*.csv")])
    if not file_clienti:
        return

    file_sedii = filedialog.askopenfilename(title="Selectează CSV tabela_sedii_secundare",
                                            filetypes=[("CSV files", "*.csv")])
    if not file_sedii:
        return

    conn = conectare_db()
    cursor = conn.cursor()

    # import tabela_date_clienti
    with open(file_clienti, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # verificăm dacă clientul există după CUI sau Reg_Comert
            cursor.execute("SELECT Nr_Crt FROM tabela_date_clienti WHERE Cui=%s OR Reg_Comert=%s",
                           (row['Cui'], row.get('Reg_Comert')))
            result = cursor.fetchone()
            if result:
                # update
                id_client = result[0]
                placeholders = ", ".join(f"{k}=%s" for k in row.keys() if k != "Nr_Crt")
                values = [row[k] for k in row.keys() if k != "Nr_Crt"]
                values.append(id_client)
                cursor.execute(f"UPDATE tabela_date_clienti SET {placeholders} WHERE Nr_Crt=%s", values)
            else:
                # insert
                columns = ", ".join(row.keys())
                placeholders = ", ".join(["%s"] * len(row))
                values = list(row.values())
                cursor.execute(f"INSERT INTO tabela_date_clienti ({columns}) VALUES ({placeholders})", values)

    # import tabela_sedii_secundare
    with open(file_sedii, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # verificăm dacă punctul de lucru există după Id_Client și Serie_Amef
            cursor.execute("SELECT 1 FROM tabela_sedii_secundare WHERE Id_Client=%s AND Serie_Amef=%s",
                           (row['Id_Client'], row['Serie_Amef']))
            if cursor.fetchone():
                # update
                placeholders = ", ".join(f"{k}=%s" for k in row.keys() if k not in ["Id_Client", "Serie_Amef"])
                values = [row[k] for k in row.keys() if k not in ["Id_Client", "Serie_Amef"]]
                values.extend([row['Id_Client'], row['Serie_Amef']])
                cursor.execute(f"UPDATE tabela_sedii_secundare SET {placeholders} WHERE Id_Client=%s AND Serie_Amef=%s", values)
            else:
                # insert
                columns = ", ".join(row.keys())
                placeholders = ", ".join(["%s"] * len(row))
                values = list(row.values())
                cursor.execute(f"INSERT INTO tabela_sedii_secundare ({columns}) VALUES ({placeholders})", values)

    conn.commit()
    conn.close()
    messagebox.showinfo("Succes", "Baza de date a fost importată cu succes!")

# =========================
# UI SETUP
# =========================
root = tk.Tk()
root.title("Gestionare Client și Sediu")
root.geometry("1400x700")

color_client = "#d0e1f9"
color_sediu = "#f9f1d0"

# -------------------------
# FRAME CLIENT (stânga)
# -------------------------
frame_client = tk.LabelFrame(root, text="Date Client", bg=color_client, padx=10, pady=10, font=("Arial", 12, "bold"))
frame_client.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)

client_labels = ["CUI Client", "Nume firmă", "Adresă sediu", "Registrul Comertului",
                 "Plătitor TVA", "Administrator Firma", "Status Firma", "Numar Telefon", "Adresa mail"]
entries = {}

for i, label in enumerate(client_labels):
    tk.Label(frame_client, text=label, bg=color_client, font=("Arial", 10)).grid(row=i, column=0, sticky="w", padx=5,
                                                                                 pady=2)
    e = tk.Entry(frame_client, width=40)
    e.grid(row=i, column=1, sticky="w", padx=5, pady=2)
    entries[label] = e

(entry_cui, entry_nume, entry_adresa, entry_reg_comert,
 entry_tva, entry_administrator, entry_status_firma,
 entry_telefon, entry_mail) = [entries[label] for label in client_labels]

# -------------------------
# FRAME SEDIU/AMEF (dreapta)
# -------------------------
frame_sediu = tk.LabelFrame(root, text="Sediu Secundar / AMEF", bg=color_sediu, padx=10, pady=10,font=("Arial", 12, "bold"))
frame_sediu.grid(row=0, column=1, sticky="nsew", padx=10, pady=5)

sediu_labels = ["Punct de lucru", "Model Amef", "Serie Amef", "Nui Amef",
                "Data conectare Anaf", "Tehnician Service", "Data expirare abonament",
                "Valoare contract - RON", "Tip Abonament", "Numar Contract"]

for i, label in enumerate(sediu_labels):
    tk.Label(
        frame_sediu,
        text=label,
        bg=color_sediu,
        font=("Arial", 10)
    ).grid(row=i, column=0, sticky="w", padx=5, pady=2)

    if label in ("Data conectare Anaf", "Data expirare abonament"):
        e = DateEntry(
            frame_sediu,
            width=37,
            date_pattern="yyyy-mm-dd"  # compatibil MySQL
        )
    else:
        e = tk.Entry(frame_sediu, width=40)

    e.grid(row=i, column=1, sticky="w", padx=5, pady=2)
    entries[label] = e


(entry_punct_lucru, entry_model_amef, entry_serie_amef, entry_nui,
 entry_conectare_anaf, entry_tehnician, entry_data_exp, entry_val_ctr,
 entry_tip_abonament, entry_nr_ctr) = [entries[label] for label in sediu_labels]

# -------------------------
# FRAME BUTOANE
# -------------------------
frame_butoane = tk.Frame(root)
frame_butoane.grid(row=1, column=0, columnspan=3, pady=10)

btn_params = [
    ("Caută cu API", lambda: cauta_firma(), "#cfe2f3"),
    ("Salvează client", lambda: salveaza_client(), "#cfe2f3"),
    # ("Modifică date client", lambda: modifica_date_client(), "#cfe2f3"),
    ("Modifica Tenhician", lambda: modifica_tehnician(), "#cfe2f3"),
    ("Verifică TVA (ANAF)", lambda: webbrowser.open_new("https://www.anaf.ro/RegistruTVA/"), "#cfe2f3"),
    ("Resetare câmpuri", lambda: resetare_toate_campurile(), "#cfe2f3"),
    ("Arata abonamente",lambda :alerta_abonamente_color(),"#ffd966"),
    # ("Export Baza Date", lambda :export_csv(),"#cfe2f3"), #  decomentezi daca vrei butoanele de import export pe interfata
    # ("Import Baza Date", lambda :import_csv(),"#cfe2f3"),
    ("Șterge client", lambda: sterge_client(), "#f28c8c"),  # roșu
    ("Șterge punct lucru", lambda: sterge_punct(), "#f28c8c"),  # roșu

]

for i, (text, cmd, color) in enumerate(btn_params):
    tk.Button(frame_butoane, text=text, command=cmd, width=16, bg=color, font=("Arial", 10, "bold")).grid(row=i // 4,column=i % 4, pady=5)

# -------------------------
# FRAME TREE + SEARCH (sub butoane)
# -------------------------
frame_tree = tk.Frame(root)
frame_tree.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

# Mutăm câmpul de căutare aici și facem entry-ul mai mare
search_frame = tk.Frame(frame_tree)
search_frame.pack(fill="x", pady=5)

tk.Label(search_frame, text="Caută client după nume sau CUI:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
search_entry = tk.Entry(search_frame, width=50)  # mai mare
search_entry.pack(side="left", padx=5)
tk.Button(search_frame, text="Caută", command=cauta_in_treeview, bg="#d4f0d0", width=12).pack(side="left", padx=5)
# tk.Button(search_frame, text="Resetează", command=incarca_dropdown_puncte, bg="#f0d0d0", width=12).pack(side="left", padx=5)

# Buton resetare camp cautare
tk.Button(search_frame, text="Resetează", command=resetare_camp_cautare, bg="#f0d0d0", width=12).pack(side="left", padx=5)

# =========================
# TREEVIEW REZULTATE (SUB CAUTARE)
# =========================

frame_tabel=tk.Frame(frame_tree)
frame_tabel.pack(fill="both", expand=True)

# search_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
scroll_y = tk.Scrollbar(frame_tabel, orient="vertical")
scroll_x = tk.Scrollbar(frame_tabel, orient="horizontal")

columns = (
    "Nr_Crt", "Nume Firma", "Cod Fiscal", "Sediu Social",
    "Nr Telefon", "Mail", "Reg Comert", "Tva", "Administrator", "Status Firma",
    "Punct Lucru", "Model AMEF", "Serie AMEF", "NUI",
    "Tehnician srv", "Data Conectare Anaf", "Data Exp. Abonament", "Val_Ctr", "Tip Abonament", "Nr_Ctr",

)
tree = ttk.Treeview(
    frame_tabel,
    columns=columns,
    show="headings",
    yscrollcommand=scroll_y.set,
    xscrollcommand=scroll_x.set
)
tree.tag_configure("expirat", background="#f28c8c")     # roșu
tree.tag_configure("avertizare", background="#fff3b0")  # galben
tree.tag_configure("valid", background="#d4f7d4")       # verde

scroll_y.config(command=tree.yview)
scroll_x.config(command=tree.xview)

scroll_y.pack(side="right", fill="y")
scroll_x.pack(side="bottom", fill="x")
tree.pack(fill="both", expand=True)
tree.bind("<<TreeviewSelect>>", populare_campuri_treeview) # cu linia asta activam functia de populare campuri cand selectam din cautare

for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=130, anchor="w")


# Meniu
meniu = tk.Menu(root)
root.config(menu=meniu)

abonamente_menu = tk.Menu(meniu, tearoff=0)
meniu.add_cascade(label="Abonamente", menu=abonamente_menu)
abonamente_menu.add_command(label="Verifică abonamente", command=alerta_abonamente_color)

import_export_menu = tk.Menu(meniu, tearoff=0)
export_menu = tk.Menu(meniu, tearoff=0)
meniu.add_cascade(label="Importa/Exporta", menu=import_export_menu)
import_export_menu.add_command(label="Importa baza date", command=import_csv)
import_export_menu.add_command(label="Exporta baza date", command=export_csv)


# CONFIGURARE GRID ROOT
root.grid_rowconfigure(3, weight=1)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

# --- POP-UP ALERTĂ ABONAMENTE ---
root.after(100, alerta_abonamente_color)  # rulează pop-up-ul automat după ce UI-ul principal e gata

footer = tk.Label(root, text="Designed by Pop Ciprian, © 2026 - Copywrit Edition",
                  font=("Arial", 8, "italic"), fg="gray")
footer.grid(row=4, column=0, columnspan=2, sticky="e", padx=10, pady=5)

root.mainloop()

