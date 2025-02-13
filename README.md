# Work in progresss! 
# My favorite* data visualization: Bivariate Choropleths 
*These maps are fun to make and pack a lot of information into a small space. However, they can be difficult to read and interpret. It's realistically not a visualization I would recommend for routing reporting or most practical use cases, but they can be eye catching. I'll take a stab at making one and describe the process.

## Output 
Here is the output - a map of San Diego county, shaded according to the interaction of two variables: Population in 2020 Census vs. Population Change 2010 to 2020 Census. The plot on the right adds a layer showing wildfire perimeters since 1980. Altogether, these datasets might come together to answer a question like: "What fast-growing or highly populated areas of SD county are likely at higher wildfire risk?" 

![image](pop_vs_pop_change.png)

Inspired by: https://waterprogramming.wordpress.com/2022/09/08/bivariate-choropleth-maps/

## Process steps
- Collect public data on 2 or more variables of interest. I chose:
    - 2020 Census population for San Diego County, by ZIP code, from opendata.sandag.org
    - 2010 Census population for San Diego County, by ZIP code, from opendata.sandag.org
    - Historical Wildfire Perimeters from the California State Geoportal, gis.data.ca.gov
    - wkt geometry (as polygons**) of ZIP codes in San Diego county from 

- Prepare a combined dataset. Population data exists at ZIP code level, but wildfire data covers continuous space. If I'm interested in exploring both variables against each other, I'll have to find a way to map them against each other.
    - An easy way to do this would be a simple spatial join wildfire perimeters onto ZIP codes: which (or many) wildfires have burned in this ZIP code? 
    - A slightly more interesting and informative way is to create a grid of pixels over the area of interest. This allows us to change the resolution at which we work. We could work with 1km x 1km pixels if we're interested in neighborhood-level dynamics, or much larger pixels if that better suits that constraints of the problem and computational needs.  
- To create the grid, I first find the extents of all ZIP codes in San Diego county. I then:
    - Generate pixels according to a parameter `cell_size` covering the extents. I tried a few values for `cell_size` but squares of 1km to a few hundred meters seem to make the most sense. 
    - Use a spatial join to trim that grid of pixels to only the areas covered by a ZIP codes (i.e., eliminating ocean areas)
    - To further illustrate, I plot a variable of interest - in this case, number of wildfires historically observed in a 1km-square pixel - as a color scale against the grid of pixels. 

![image](process_plot.png)

- From there, I use a combination of relational and spatial joins to create a geoDataFrame storing, for each pixel, its geometry, its population in 2020, 2010, the % change in population between 2010 and 2020, and the number of wildifre perimeters intersecting that square kilometer since 1980. 
- Colorscale: I defined the colorscale as a 3x3 grid of colors to mimic the example. Each pixel is assigned a color based on the quantile it ranks in 2 variables (bottom, middle, or top third).

**fun fact: ZIP codes are actually not polygons contiguously covering a city, the way we might thinkg of them. Technically, according to the postal service, they are collections of street addresses. As new roads and addresses are developed, the boundaries of ZIP codes change. However, for practical purposes, many ZIP code shapefiles like this one are available as polygons, which is much easier to work with. 

## Readability considerations and other ideas 
- Red vs. Blue: to mimic the example, I used a teal/pink/purple colorscale. (Accidental Padres alt. colors?). A blue/red/purple or yellow/blue/green colorscale might be more easily interetable as more readers are familiar with those color combinations. 
- 3x3 vs 4x4: in addition to experimenting with different colormap endpoints, would a more continuous-appearing colorscale improve readability? Might try this out.
- Basemap and Interaction: it would be much more user-friendly to map this on a zoomable HTML object, with a basemap and (possibly) with the ability to toggle layers on or off. This can be done with a little extra working using Folium. 
- Infrequent events: Aggregating the number of fires per square-km didn't work as well as I had hoped. It looks relatively informative in the first plot above (yellow/green/purple), but fires are rare enough that the percentile-based color selection doesn't work well. Most pixels have 0 or 1 fire perimeter since 1980, making for an uninteresting and uninformative amount of variation in the data. Consider if there are other ways to summarize or map infrequently-ocurring events. 