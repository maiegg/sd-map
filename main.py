import pandas as pd 
import json 
import numpy as np 
import matplotlib.pyplot as plt 
import geopandas as gpd
from shapely import wkt
from shapely.geometry import Polygon, Point
# import contextily as ctx

def read():
    pop2010 = pd.read_csv('2010_Census_Population_by_ZIP_Code_20250210.csv', dtype=str)
    pop2010.population = pop2010.population.astype(int)
    pop2010 = pop2010.groupby(['zip','yr_id']).population.sum().reset_index()

    pop2020 = pd.read_csv('2020_Census_Population_by_Age__Sex_and_Ethnicity_by_ZIP_Code_20250210.csv', dtype=str)
    pop2020.population = pop2020.population.astype(int)
    pop2020 = pop2020.groupby(['zip','yr_id']).population.sum().reset_index()

    fires = gpd.read_file('California_Fire_Perimeters_(all).geojson')
    zips = gpd.read_file('California_Fire_Perimeters_(all).geojson')

    df = pd.read_csv('ZIP_CODES_20250211.csv', dtype=str)
    df['geometry'] = df['the_geom'].apply(wkt.loads)
    zips = gpd.GeoDataFrame(df, geometry='geometry',crs='EPSG:4326')
    zips = zips[['ZIP','geometry']]
    del df 
    
    return pop2010, pop2020, fires, zips



# def convert_zips_to_geojson(fn: str):
#     # Source (no CRS): https://data.sandiegocounty.gov/Maps-and-Geographical-Resources/Zip-Codes/vsuf-uefy
    
#     import pandas as pd
#     import geopandas as gpd
#     from shapely import wkt

#     df = pd.read_csv(fn)
#     df['geometry'] = df['the_geom'].apply(wkt.loads)
#     gdf = gpd.GeoDataFrame(df, geometry='geometry')
#     gdf.drop(columns=['the_geom'], inplace=True)
#     gdf.to_file('output.geojson', driver='GeoJSON')
# try:
#     with open('output.geojson') as f:
#         zips = json.load(f)
# except:
#     convert_zips_to_geojson(fn='ZIP_CODES_20250211.csv')



# def adjust_extent(geojson_data, margin=0.05):
#     """Claculates an adjusted extent for the plot based on GeoJSON data"""
#     min_lon, min_lat, max_lon, max_lat = 180, 90, -180, -90
    
#     for feature in geojson_data['features']:
#         geometry = feature['geometry']
#         coords = np.array(geometry['coordinates'])

#         # Expect only polygons or multipolys;  
#         for coord_set in coords:
#             if geometry['type'] in 'Polygon':
#                 for sub_coord_set in coord_set:
#                     min_lon = min(min_lon, *sub_coord_set[:, 0])
#                     max_lon = max(max_lon, *sub_coord_set[:, 0])
#                     min_lat = min(min_lat, *sub_coord_set[:, 1])
#                     max_lat = max(max_lat, *sub_coord_set[:, 1])
            
#     lon_margin = (max_lon - min_lon) * margin
#     lat_margin = (max_lat - min_lat) * margin

#     return [min_lon - lon_margin, max_lon + lon_margin, min_lat - lat_margin, max_lat + lat_margin]

# def plot_geojson(geojson_data, ax=None):
#     """Plots GeoJSON data on a Matplotlib axes"""
#     if ax is None:
#         fig, ax = plt.subplots(figsize=(10,10), subplot_kw={'projection':ccrs.Mercator()})

#     for feature in geojson_data['features']:
#         geometry = feature['geometry']
#         coords = np.array(geometry['coordinates'])

#         ax.fill(coords[0][:, 0], coords[0][:, 1], '-g', alpha=0.5)

###########################################################################

# Read 
pop2010, pop2020, fires, zips  = read()

# Calculate ZIP extents
minx, miny, maxx, maxy = zips.geometry.total_bounds

# Create grid of ~1000-meter squares 
cell_size = 0.01 # degrees 

grid = []  
grid_centroids = [] 

x0 = minx 
y0 = miny 

while x0 < maxx:   
    while y0 < maxy:
        grid.append(
            Polygon([
                (x0,y0)
                ,(x0+cell_size, y0)
                ,(x0+cell_size, y0+cell_size)
                ,(x0, y0+cell_size)
                # ,(x0, y0)  # can't remember if need to repeat first point in cycle
            ])
        )

        grid_centroids.append(
            Point([x0 + cell_size/2, y0 + cell_size/2])
        )
        y0 += cell_size
    x0 += cell_size
    y0 = miny

grid = gpd.GeoDataFrame({'geometry': grid}, crs='EPSG:4326')
grid_centroids = gpd.GeoDataFrame({'geometry': grid_centroids}, crs='EPSG:4326')

grid['grid_idx'] = grid.index
grid_centroids['grid_idx'] = grid_centroids.index

grid_centroids = pd.merge(
    grid_centroids
    ,grid.rename({'geometry':'polygon_geometry'}, axis=1)
    ,left_on='grid_idx'
    ,right_on='grid_idx'
)

# Filter grid_centroids to only those touching a ZIP, using a spatial join 
grid_centroids = gpd.sjoin(grid_centroids, zips, how='inner', predicate='intersects')\
    .to_crs(grid_centroids.crs)\
    .drop('index_right', axis=1)
print(f'{len(grid_centroids)} grid squares touching a ZIP code')

if False:
    # Check: plot squares and ZIPs on top of each other 
    fig, ax = plt.subplots()
    zips.plot(ax=ax)
    grid_centroids.plot(ax=ax, alpha=0.1, fc='red')
    plt.show()

grid_summary = grid_centroids.copy()
grid_summary.rename({'geometry':'centroid_geometry', 'polygon_geometry':'geometry'}, axis=1, inplace=True)
print(f'{len(grid_summary.grid_idx.unique())} grid squares; ({len(grid_summary)} rows). This dataset should be distinct on grid_idx')

# 2 | Spatial join fires onto grid centroids and aggregate; join back to mapDf
grid_fire = gpd.sjoin(grid_centroids, fires, how='inner', predicate='intersects').to_crs(grid_centroids.crs)
grid_fire_out = grid_fire.groupby('grid_idx').STATE.count().reset_index().rename({'STATE':'num_fires'}, axis=1).reset_index() # number of fires 
top20pct = grid_fire.Shape__Area.quantile(0.8)
grid_fire_out = pd.merge(
    grid_fire_out
    ,grid_fire[grid_fire.Shape__Area >= top20pct].groupby('grid_idx').STATE.count().reset_index().rename({'STATE':'num_major_fires'}, axis=1)
    ,how='left'
    ,left_on='grid_idx'
    ,right_on='grid_idx'
)
print(f'{len(grid_fire_out.grid_idx.unique())} grid squares with fires observed ({len(grid_fire_out)} rows). This dataset should be distinct on grid_idx')

# 3 | Relational join Populations onto ZIPs 
print(zips.head())
zips_pop = pd.merge(
    zips, 
    pop2010[['zip','population']].rename({'population':'population_2010','zip':'ZIP'},axis=1),
    how='left',
    left_on='ZIP',
    right_on='ZIP'
)
zips_pop = pd.merge(
    zips_pop, 
    pop2020[['zip','population']].rename({'population':'population_2020','zip':'ZIP'},axis=1),
    how='left',
    left_on='ZIP',
    right_on='ZIP'
)
zips_pop = zips_pop.drop_duplicates(subset='ZIP', keep='first')
print(f'{len(zips_pop)} rows / {len(zips_pop.ZIP.unique())} ZIPs with population data; {len(zips)} ZIP codes original')

# 4 | Relational join Populations back onto grid_summary via ZIP
grid_summary = pd.merge(
    grid_summary
    ,zips_pop[['ZIP','population_2010','population_2020']]
    ,how='left'
    ,left_on='ZIP'
    ,right_on='ZIP'
)
print(
    f'{len(grid_summary)} rows to map; {len(grid_summary.grid_idx.unique())} grid squares; {len(grid_summary.ZIP.unique())} ZIPs'
)

# 5 | Relational join fire info back onto grid_summary via grid_idx 
grid_summary = pd.merge(
    grid_summary
    ,grid_fire_out[['grid_idx','num_fires','num_major_fires']]
    ,how='left'
    ,left_on='grid_idx'
    ,right_on='grid_idx'
)

# Check: can we plot a univariate pixel map?
if False:
    fig, ax = plt.subplots()
    grid_summary.plot(ax=ax, column='population_2020', cmap='viridis')
    plt.show()

# 6 | Set up bivariate color scale(s) using option 1 - continuous, simple 
# def create_color(gdf: gpd.GeoDataFrame, var1: str, var2: str):
#     from sklearn.preprocessing import MinMaxScaler
#     scaler = MinMaxScaler()
#     gdf[['var1_norm', 'var2_norm']] = scaler.fit_transform(gdf[[var1, var2]])
#     gdf['color'] = gdf.apply(lambda row: (row['var1_norm'], 0, row['var2_norm']), axis=1)
#     return gdf
# grid_summary = grid_summary.to_crs(epsg=3857)

# Define the 3x3 color grid
color_grid = [
    ["#e8e8e8", "#d495bb", "#be64ac"],  # Top row (high var1)
    ["#a0a8cc", "#7b72a0", "#553a75"],  # Middle row
    ["#5ac8c8", "#489ca1", "#3b4994"]   # Bottom row (low var1)
]

def assign_color(var1, var2):
    # Determine the quantile bins (0-33%, 34-66%, 67-100%)
    var1_bins = pd.qcut(var1, q=3, labels=[2, 1, 0])  # 2 = bottom, 1 = middle, 0 = top
    var2_bins = pd.qcut(var2, q=3, labels=[0, 1, 2])  # 0 = left, 1 = middle, 2 = right
    
    # Create a DataFrame to store the colors
    color_map = []
    for i, j in zip(var1_bins, var2_bins):
        if (i >= 0) and (j >= 0): # hacky way to get rid of nan's 
            color_map.append(color_grid[i][j])
        else:
            color_map.append('#000000')
    return color_map

# 7 | Plot 
grid_summary['pop_change_abs'] = grid_summary['population_2020'] - grid_summary['population_2010']
grid_summary['pop_change_pct'] = grid_summary['pop_change_abs'] / grid_summary['population_2020']

def plot(grid_summary, var1, var2, fOut):

    grid_summary['color'] = assign_color(var1=grid_summary[var1], var2=grid_summary[var2])

    # Plotting the data with the color grid as the legend
    fig, (ax, ax_legend) = plt.subplots(1, 2, figsize=(12, 6), gridspec_kw={'width_ratios': [6, 1]})

    # Scatter plot of the data
    grid_summary.plot(ax=ax, color=grid_summary['color'], edgecolor=None, alpha=0.75)
    ax.set_title(f'{var1} vs. {var2}', fontsize=14, weight='bold')

    # Plot the color grid as the legend
    for i in range(3):
        for j in range(3):
            ax_legend.add_patch(plt.Rectangle((j, 2 - i), 1, 1, color=color_grid[i][j]))

    ax_legend.set_xlim(0, 3)
    ax_legend.set_ylim(0, 3)
    ax_legend.set_xticks([])
    ax_legend.set_yticks([])
    ax_legend.set_xlabel(var1)
    ax_legend.set_ylabel(var2)
    ax_legend.set_aspect('equal')
    ax_legend.set_title('Legend', fontsize=12, weight='bold')

    plt.tight_layout()
    plt.savefig(fOut)

# Pop vs. Pop growth 
plot(grid_summary=grid_summary, var1='population_2020', var2='pop_change_pct', fOut='pop_vs_pop_change.png')

# # Pop vs. Pop density
# plot(grid_summary=grid_summary, var1='population_2020', var2='pop_change_pct')

# # Pop vs. Fires 
# plot(grid_summary=grid_summary, var1='population_2020', var2='num_fires', fOut='pop_vs_fires.png')

# Pop Growth vs. Fires
# plot(grid_summary=grid_summary, var1='pop_change_pct', var2='num_fires', fOut='pgop_change_vs_fires.png')

# Pop Density vs. Fires 

# TODO:
# Add basemap 

