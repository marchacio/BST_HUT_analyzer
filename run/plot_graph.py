import matplotlib.pyplot as plt

#--------------------------------------------------
# W/P RATIO
#--------------------------------------------------

# La tua lista di valori
dati = [

]

# Crea il grafico
plt.plot(dati, linestyle='-')

# Aggiunge un titolo e le etichette agli assi
plt.title("Rapporto W/P")
plt.xlabel("Tag (versioni)")
plt.ylabel("Ratio W/P")


# Aggiunge una griglia personalizzata
plt.grid(True, color='lightgray', linestyle='--', linewidth=0.5)

# Salva il grafico in un file immagine
plt.savefig("grafico_wp_ratio.png")

print("Il grafico è stato salvato")

plt.close()


#--------------------------------------------------
# Max Line Length
#--------------------------------------------------

# La tua lista di valori
dati = [

]

# Crea il grafico
plt.plot(dati, linestyle='-')

# Aggiunge un titolo e le etichette agli assi
plt.title("Lunghezza massima della riga")
plt.xlabel("Tag (versioni)")
plt.ylabel("caratteri")


# Aggiunge una griglia personalizzata
plt.grid(True, color='lightgray', linestyle='--', linewidth=0.5)

# Salva il grafico in un file immagine
plt.savefig("grafico_max_line.png")

print("Il grafico è stato salvato")