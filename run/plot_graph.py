import matplotlib.pyplot as plt

#--------------------------------------------------
# W/P RATIO
#--------------------------------------------------

# La tua lista di valori
dati = [
    #77.0,77.0,77.0,77.0,77.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,1404.0
    0.34005258545135847,0.3353500432152118,0.3353500432152118,0.3356401384083045,0.3356401384083045,0.23167848699763594,0.2327790973871734,0.2327790973871734,0.2327790973871734,0.2327790973871734,0.2327790973871734,0.2327790973871734,0.2327790973871734,0.25645592163846836,0.25783348254252464,0.25783348254252464,0.25783348254252464,0.25783348254252464,0.25622775800711745,0.25902527075812276,0.25902527075812276,0.25902527075812276,0.25902527075812276,0.25902527075812276,0.25902527075812276,0.25902527075812276,0.25902527075812276,0.25902527075812276,0.25902527075812276,0.6360981308411215
]

# Crea il grafico
plt.plot(dati, marker='o', linestyle='-')

# Aggiunge un titolo e le etichette agli assi
plt.title("Andamento del rapporto W/P")
plt.xlabel("Tag (versioni)")
plt.ylabel("Ratio W/P")


# Aggiunge una griglia personalizzata
plt.grid(True, color='lightgray', linestyle='--', linewidth=0.5)

# Salva il grafico in un file immagine
plt.savefig("grafico_rc_ratio.png")

print("Il grafico è stato salvato")

plt.close()


#--------------------------------------------------
# Max Line Length
#--------------------------------------------------

# La tua lista di valori
dati = [
    77.0,77.0,77.0,77.0,77.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,136.0,1404.0
]

# Crea il grafico
plt.plot(dati, marker='o', linestyle='-')

# Aggiunge un titolo e le etichette agli assi
plt.title("Andamento della lunghezza massima della riga")
plt.xlabel("Tag (versioni)")
plt.ylabel("Lunghezza massima della riga (caratteri)")


# Aggiunge una griglia personalizzata
plt.grid(True, color='lightgray', linestyle='--', linewidth=0.5)

# Salva il grafico in un file immagine
plt.savefig("grafico_max_line.png")

print("Il grafico è stato salvato")