"""
Mapa de Referência - Polos Produtivos NIA$
América do Sul com destaque para Colômbia e Venezuela
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Polygon
import numpy as np

# Configuração do estilo
plt.style.use('dark_background')
fig, ax = plt.subplots(1, 1, figsize=(14, 16), facecolor='#0d1117')
ax.set_facecolor('#0d1117')

# Contorno simplificado dos países da América do Sul (coordenadas aproximadas)
countries = {
    'Brasil': {
        'color': '#238636',
        'coords': [
            [-35, -5], [-40, -5], [-45, -10], [-50, -15], [-55, -20], [-60, -25],
            [-65, -30], [-70, -25], [-75, -15], [-75, -5], [-70, 5], [-60, 5],
            [-50, 5], [-45, 0], [-40, -5], [-35, -5]
        ]
    },
    'Argentina': {
        'color': '#58a6ff',
        'coords': [
            [-58, -22], [-63, -25], [-68, -30], [-70, -35], [-72, -40], [-72, -50],
            [-68, -55], [-65, -52], [-60, -48], [-57, -42], [-55, -35], [-57, -30],
            [-58, -25], [-58, -22]
        ]
    },
    'Chile': {
        'color': '#a371f7',
        'coords': [
            [-70, -20], [-72, -25], [-74, -30], [-75, -35], [-76, -40], [-76, -45],
            [-75, -50], [-73, -52], [-71, -48], [-70, -42], [-69, -35], [-68, -28],
            [-69, -22], [-70, -20]
        ]
    },
    'Peru': {
        'color': '#d29922',
        'coords': [
            [-80, -5], [-82, -10], [-78, -15], [-76, -18], [-72, -18], [-70, -15],
            [-69, -10], [-70, -5], [-72, 0], [-75, 2], [-78, 0], [-80, -5]
        ]
    },
    'Bolívia': {
        'color': '#8b949e',
        'coords': [
            [-65, -10], [-70, -12], [-72, -15], [-70, -20], [-65, -22], [-60, -20],
            [-58, -15], [-60, -12], [-63, -10], [-65, -10]
        ]
    },
    'Paraguai': {
        'color': '#3fb950',
        'coords': [
            [-58, -20], [-62, -22], [-62, -25], [-58, -27], [-55, -25], [-54, -22],
            [-55, -20], [-58, -20]
        ]
    },
    'Uruguai': {
        'color': '#79c0ff',
        'coords': [
            [-53, -30], [-58, -32], [-58, -35], [-54, -37], [-50, -35], [-50, -32],
            [-52, -30], [-53, -30]
        ]
    },
    'Colômbia': {
        'color': '#f778ba',
        'coords': [
            [-78, 8], [-80, 5], [-79, 2], [-77, 0], [-75, -2], [-72, -2],
            [-70, 0], [-68, 3], [-67, 6], [-69, 9], [-72, 11], [-75, 11],
            [-77, 10], [-78, 8]
        ]
    },
    'Venezuela': {
        'color': '#ff7b72',
        'coords': [
            [-73, 12], [-75, 10], [-73, 8], [-70, 7], [-66, 7], [-63, 8],
            [-61, 10], [-60, 12], [-62, 15], [-65, 16], [-68, 15], [-71, 14],
            [-73, 12]
        ]
    },
    'Equador': {
        'color': '#ffa657',
        'coords': [
            [-81, 3], [-80, 0], [-78, -2], [-76, -1], [-75, 2], [-76, 4],
            [-78, 5], [-80, 4], [-81, 3]
        ]
    }
}

# Desenhar países
for country, data in countries.items():
    coords = np.array(data['coords'])
    polygon = Polygon(coords, closed=True, facecolor=data['color'], 
                      edgecolor='#c9d1d9', linewidth=1.5, alpha=0.3)
    ax.add_patch(polygon)
    
    # Adicionar label no centro do país
    centroid = coords.mean(axis=0)
    ax.text(centroid[0], centroid[1], country, ha='center', va='center',
            fontsize=9, fontweight='bold', color='#c9d1d9', alpha=0.8)

# Polos produtivos - COLOMBIA (latitudes positivas)
colombia_polos = [
    {'name': 'Bogotá\n(Flores)', 'lat': 4.6, 'lon': -74.2, 'color': '#f778ba'},
    {'name': 'Medellín\n(Café)', 'lat': 6.3, 'lon': -75.5, 'color': '#f778ba'},
    {'name': 'Cali\n(Cana)', 'lat': 3.3, 'lon': -76.5, 'color': '#f778ba'},
    {'name': 'Armenia\n(Café)', 'lat': 4.5, 'lon': -75.7, 'color': '#f778ba'},
    {'name': 'Cajicá\n(Flores)', 'lat': 4.7, 'lon': -73.9, 'color': '#f778ba'},
    {'name': 'Santa Marta\n(Banana)', 'lat': 11.2, 'lon': -74.2, 'color': '#f778ba'},
    {'name': 'Villavicencio\n(Palma)', 'lat': 4.1, 'lon': -73.6, 'color': '#f778ba'},
    {'name': 'Cartagena\n(Abacate)', 'lat': 10.4, 'lon': -75.5, 'color': '#f778ba'},
]

# Polos produtivos - VENEZUELA (latitudes positivas)
venezuela_polos = [
    {'name': 'Guanare\n(Milho)', 'lat': 9.0, 'lon': -69.7, 'color': '#ff7b72'},
    {'name': 'Calabozo\n(Arroz)', 'lat': 8.9, 'lon': -67.4, 'color': '#ff7b72'},
    {'name': 'Carora\n(Cana)', 'lat': 10.2, 'lon': -70.1, 'color': '#ff7b72'},
    {'name': 'Maracaibo\n(Sorgo)', 'lat': 10.7, 'lon': -71.6, 'color': '#ff7b72'},
]

# Polos produtivos - BRASIL (destaque)
brasil_polos = [
    {'name': 'Santos\n(Porto)', 'lat': -23.9, 'lon': -46.3, 'color': '#58a6ff'},
    {'name': 'Paranaguá\n(Porto)', 'lat': -25.5, 'lon': -48.5, 'color': '#58a6ff'},
]

# Plotar polos
for polo in colombia_polos:
    ax.plot(polo['lon'], polo['lat'], 'o', markersize=12, color=polo['color'], 
            markeredgecolor='white', markeredgewidth=2, zorder=5)
    ax.annotate(polo['name'], (polo['lon'], polo['lat']), 
                xytext=(10, 10), textcoords='offset points',
                fontsize=7, color='white', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#21262d', edgecolor=polo['color'], alpha=0.9))

for polo in venezuela_polos:
    ax.plot(polo['lon'], polo['lat'], 's', markersize=12, color=polo['color'], 
            markeredgecolor='white', markeredgewidth=2, zorder=5)
    ax.annotate(polo['name'], (polo['lon'], polo['lat']), 
                xytext=(10, -15), textcoords='offset points',
                fontsize=7, color='white', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#21262d', edgecolor=polo['color'], alpha=0.9))

for polo in brasil_polos:
    ax.plot(polo['lon'], polo['lat'], '^', markersize=10, color=polo['color'], 
            markeredgecolor='white', markeredgewidth=1.5, zorder=5)

# Linha do equador
ax.axhline(y=0, color='#8b949e', linestyle='--', linewidth=1, alpha=0.5, label='Equador')
ax.text(-82, 0.5, 'EQUADOR', fontsize=8, color='#8b949e', alpha=0.7)

# Configurações do gráfico
ax.set_xlim(-85, -35)
ax.set_ylim(-38, 20)
ax.set_xlabel('Longitude', fontsize=11, color='#c9d1d9')
ax.set_ylabel('Latitude', fontsize=11, color='#c9d1d9')
ax.set_title('🌎 NIA$ - Polos Produtivos da América do Sul\nColômbia (rosa) e Venezuela (vermelho) - Latitudes Positivas', 
             fontsize=14, fontweight='bold', color='#f0f6fc', pad=20)

# Legenda
legend_elements = [
    mpatches.Patch(color='#f778ba', label='🇨🇴 Colômbia - 8 polos (Café, Flores, Banana, Palma, Abacate)'),
    mpatches.Patch(color='#ff7b72', label='🇻🇪 Venezuela - 4 polos (Milho, Arroz, Cana, Sorgo)'),
    mpatches.Patch(color='#238636', label='🇧🇷 Brasil'),
    mpatches.Patch(color='#58a6ff', label='🇦🇷 Argentina'),
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#f778ba', markersize=10, label='Polo Colômbia'),
    plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='#ff7b72', markersize=10, label='Polo Venezuela'),
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=9, 
          facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9')

# Grid
ax.grid(True, alpha=0.2, color='#30363d')
ax.set_axisbelow(True)

# Anotações explicativas
ax.text(-83, 18, 'COORDENADAS CORRETAS:\n• Colômbia: latitudes POSITIVAS (4°N a 11°N)\n• Venezuela: latitudes POSITIVAS (8°N a 11°N)\n• Brasil: latitudes NEGATIVAS (abixo do equador)', 
        fontsize=9, color='#7ee787', fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#0d1117', edgecolor='#238636', alpha=0.95))

plt.tight_layout()
plt.savefig('mapa_polos_sulamerica.png', dpi=150, facecolor='#0d1117', edgecolor='none', bbox_inches='tight')
print("✅ Mapa gerado: mapa_polos_sulamerica.png")
