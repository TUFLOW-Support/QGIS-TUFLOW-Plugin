try:
    import geopandas as gpd
except ImportError:
    gpd = None


class GisMessages:
    def __init__(self):
        if gpd is None:
            raise ImportError("geopandas is required to use GisMessages. Please install it using 'pip install geopandas'.")
        self.message_data = {
            'Location': [],
            'Severity': [],
            'Text': []
        }

    def add_message(self, location, severity, text):
        self.message_data['Location'].append(location)
        self.message_data['Severity'].append(severity)
        self.message_data['Text'].append(text)

    def convert_to_gdf(self, crs):
        gdf_messages = gpd.GeoDataFrame(
            {
                'Severity': self.message_data['Severity'],
                'Message': self.message_data['Text'],
            },
            geometry=self.message_data['Location'],
            crs=crs,
        )
        return gdf_messages
