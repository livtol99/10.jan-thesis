import os
import sys
from collections import defaultdict

import community as community_louvain
import matplotlib.patches as mpatches
import networkx as nx
import pandas as pd
import prince
import numpy as np
from matplotlib import pyplot as plt
from networkx.algorithms import bipartite
from netgraph import Graph
from matplotlib.ticker import FuncFormatter




class PipelineCorAnalysis:
    """
This class provides methods to create a bipartite graph, perform sanity checks, analyze the graph's connectivity, plot degree distributions, project graphs, 
identify top markers, and perform Correspondence Analysis (CA) on the dataset.

Attributes:
    -----------
    data_subset : pd.DataFrame
        A subset of the Twitter data containing the required columns 'follower_id' and 'twitter_name'.
    edgelist_name : str
        The name of the edge list, derived from the provided data subset name.
    subset_name : str
        The name of the data subset.
    B : nx.DiGraph
        The bipartite graph created from the data subset (initialized in create_bipartite_graph method).
    G_markers : nx.Graph
        The unweighted projection of the markers (initialized in marker_projection method).
    G2_markers : nx.Graph
        The weighted projection of the markers (initialized in marker_projection method).
    partition : dict
        The partition of the graph computed by the Louvain method (initialized in calculate_communities method).
    contingency_table : pd.DataFrame
        The contingency table created for Correspondence Analysis (initialized in create_contingency_table method).
    ca : prince.CA
        The Correspondence Analysis model (initialized in perform_ca_analysis method).

    Methods:
    --------
    get_edgelist_name(data_subset_name):
        Returns the edge list name, which is identical to the provided data subset name.
    create_bipartite_graph():
        Creates a bipartite graph from the data subset.
    sanity_checks():
        Performs sanity checks on the bipartite graph.
    connectedness():
        Analyzes the connectedness of the bipartite graph.
    plot_degree_cdf():
        Plots the complementary cumulative distribution function (CCDF) for the in-degrees and out-degrees of the bipartite graph.
    top_five_markers_in_degree():
        Identifies and prints the top five markers based on in-degree centrality.
    marker_projection():
        Creates unweighted and weighted projections of the markers from the bipartite graph.
    plot_w_marker_relations():
        Plots the relationships between markers in the weighted projection graph.
    calculate_communities():
        Calculates and prints the number of communities using the Louvain method.
    perform_graph_checks():
        Runs a series of graph analysis methods.
    create_contingency_table():
        Creates a contingency table from the data subset.
    perform_ca_analysis(save_path, n_components=100, n_iter=100):
        Performs Correspondence Analysis on the contingency table and saves the results.
    plot_variance():
        Plots the percentage of variance explained by each dimension in the Correspondence Analysis.
    get_unique_filepath(filepath):
        Generates a unique file path to avoid overwriting existing files.
    perform_ca_pipeline(save_path):
        Runs the full CA pipeline: creating the contingency table, performing CA, and plotting variance.
    run_all(save_path):
        Executes all the main graph checks and the CA pipeline.
"""
    def __init__(self, data_subset, data_subset_name):
        if not isinstance(data_subset, pd.DataFrame):
            raise ValueError("data_subset must be a pandas DataFrame")

        required_columns = ['follower_id', 'twitter_name']
        if not all(column in data_subset.columns for column in required_columns):
            raise ValueError(f"data_subset must contain the following columns: {required_columns}")

        self.data_subset = data_subset
        self.edgelist_name = self.get_edgelist_name(data_subset_name)
        self.subset_name = data_subset_name  

    def get_edgelist_name(self, data_subset_name):
        """
        Returns the edge list name identical to `data_subset_name`.
        """
        # Extract the name from the DataFrame
        return data_subset_name

    # Graph checks methods
    def create_bipartite_graph(self):
        try:
            # Create a new bipartite graph
            B = nx.DiGraph()  # initialize a new directed graph

            # Add nodes with the node attribute "bipartite"
            B.add_nodes_from(self.data_subset['follower_id'].unique(), bipartite=0)  # adding a node for each unique follower. Bipartite = 0 assigns followers to the first set in the graph.  Set 1 in the bipartite graph
            B.add_nodes_from(self.data_subset['twitter_name'].unique(), bipartite=1)  # adding a node for each unique marker. Set 2 in the bipartite graph

            # Add edges
            B.add_edges_from(list(zip(self.data_subset['follower_id'], self.data_subset['twitter_name'])))  # edges are directed from the first to the second element. So direction is; follower --> Marker

            self.B = B  # store the graph in an instance variable for later use
            
            #call the sanity check method here to avoid AttributeErrors 
            # self.sanity_checks()
            # self.connectedness()
            # self.plot_degree_cdf()
        except Exception as e:
            print(f"Error occurred while creating bipartite graph: {str(e)}")
    
    def sanity_checks(self):
        if not hasattr(self, 'B'):
            raise AttributeError("Bipartite graph not created. Call create_bipartite_graph first.")
        num_nodes = self.B.number_of_nodes()
        num_edges = self.B.number_of_edges()
        num_rows = len(self.data_subset)

        print("Number of nodes:", num_nodes)
        if num_edges == num_rows:
            print("Edge number is sane - matches the number of rows in the inputted edgelist")

        B_undirected = self.B.to_undirected()
        print("Is the graph connected?", nx.is_connected(B_undirected))

    def connectedness(self):
        # Calculate weakly connected components
        weakly_connected_components = list(nx.weakly_connected_components(self.B))

        # Print the number of weakly connected components
        print("Number of weakly connected components:", len(weakly_connected_components))

        # Print the size of the largest weakly connected component
        print("Size of largest weakly connected component:", max(len(c) for c in weakly_connected_components))

        # Calculate strongly connected components
        strongly_connected_components = list(nx.strongly_connected_components(self.B))

        # Print the number of strongly connected components
        print("Number of strongly connected components:", len(strongly_connected_components))

        # Print the size of the largest strongly connected component
        print("Size of largest strongly connected component:", max(len(c) for c in strongly_connected_components))
    
    def plot_degree_cdf(self):
        followers = [n for n, d in self.B.nodes(data=True) if d['bipartite']==0]
        markers = [n for n, d in self.B.nodes(data=True) if d['bipartite']==1]

        in_degrees = [d for n, d in self.B.in_degree(markers)]
        out_degrees = [d for n, d in self.B.out_degree(followers)] #get out degrees for followers

        degrees_out = np.array(out_degrees)
        degrees_in = np.array(in_degrees)

        # Calculate the complementary cumulative distribution function (CCDF) for out_degrees
        counts, bin_edges = np.histogram(degrees_out, bins=range(1, max(degrees_out) + 1), density=True)
        cum_counts = np.cumsum(counts)
        ccdf = 1 - cum_counts

        # Plot the CCDF on a log-log scale
        plt.figure(figsize=(10, 7))
        plt.loglog(bin_edges[:-1], ccdf, marker='.')
        plt.xlabel('Degree (k)')
        plt.ylabel('Log-Log Probability of Degree Greater Than x')

        # Include subset_name in the title
        plt.title(f'Out-Degree Distribution for {self.subset_name}')

        plt.show()

        # Calculate the complementary cumulative distribution function (CCDF)for in_degrees 
        counts, bin_edges = np.histogram(degrees_in, bins=range(1, max(degrees_in) + 1), density=True)
        cum_counts = np.cumsum(counts)
        ccdf = 1 - cum_counts

        # Plot the CCDF on a log-log scale
        plt.figure(figsize=(10, 7))
        plt.loglog(bin_edges[:-1], ccdf, marker='.', color='green')
        plt.xlabel('Degree (k)')
        plt.ylabel('Log-Log Probability of Degree Greater Than x')

        # Include subset_name in the title
        plt.title(f'In-Degree Distribution for {self.subset_name}')

        plt.show()
    
    def top_five_markers_in_degree(self):
        # Calculate in-degree centrality for each node in the graph
        in_degree_centrality = nx.in_degree_centrality(self.B)

        # Filter the nodes to only include markers
        markers = [n for n, d in self.B.nodes(data=True) if d['bipartite']==1]
        marker_in_degree = {marker: in_degree_centrality[marker] for marker in markers}

        # Sort the markers by in-degree centrality and select the top five
        top_five_markers = sorted(marker_in_degree.items(), key=lambda item: item[1], reverse=True)[:5]

        # Print the top five markers and their types
        for marker, centrality in top_five_markers:
            marker_type = self.data_subset[self.data_subset['twitter_name'] == marker]['type2'].iloc[0]
            print(f"Marker: {marker}, Type: {marker_type}, In-Degree Centrality: {centrality}")
    
    def marker_projection(self):
        if not hasattr(self, 'B'):
            raise AttributeError("Bipartite graph not created. Call create_bipartite_graph first.")
        # Separate nodes into two sets
        followers, markers = bipartite.sets(self.B) #first set is followers (set 0) and second is markers (set 1)

        # Convert to undirected graph
        B_undirected = self.B.to_undirected()

        # Create the projection for markers
        G_markers = bipartite.projected_graph(B_undirected, markers) #unweighted projection

        # Weighted projection for markers
        G2_markers = bipartite.weighted_projected_graph(B_undirected, markers)

        # Store the projections for later use
        self.G_markers = G_markers
        self.G2_markers = G2_markers
    
    def plot_w_marker_relations(self):
        if not hasattr(self, 'G2_markers'):
            self.marker_projection()
        color_dict = {'consumption': 'blue', 'information': 'yellowgreen', 'football clubs': 'mediumvioletred', 'education': 'darkorange'}

        # Get the unique types and assign a color to each one
        unique_types = self.data_subset['type2'].unique()
        type_color = {utype: color_dict.get(utype, 'gray') for utype in unique_types}  # Use gray for missing types

        # Create a dictionary that maps each twitter_name to its type
        twitter_name_to_type = dict(zip(self.data_subset['twitter_name'], self.data_subset['type2']))

        # Create a list of colors for each node in the graph
        node_colors = [type_color[twitter_name_to_type.get(node, 'gray')] for node in self.G2_markers.nodes()]  # Use gray for missing types

        # Draw the graph with node colors
        plt.figure(figsize=(10, 10))  # Increase figure size
        pos = nx.spring_layout(self.G2_markers, weight='weight')  # Use spring layout

        # Draw edges with increased alpha
        nx.draw_networkx_edges(self.G2_markers, pos, alpha=0.09, width=0.1)

        # Draw nodes with original alpha and node colors
        nx.draw_networkx_nodes(self.G2_markers, pos, node_color=node_colors, node_size=40, alpha=0.5)

        # Calculate the center of the graph by averaging the positions of all nodes
        center = np.array([0.0, 0.0])  # Initialize as float array
        for coord in pos.values():
            center += np.array(coord)
        center /= len(pos)

        # Define the distance for nodes to be considered "outside the main cluster"
        distance = 0.7

        # Draw labels for nodes outside the main cluster
        for node, coord in pos.items():
            if np.linalg.norm(np.array(coord) - center) > distance:
                plt.text(coord[0] + 0.02, coord[1] + 0.02, node, fontsize=7)

        # Create legend
        patches = [mpatches.Patch(color=color, label=utype) for utype, color in type_color.items()]
        plt.legend(handles=patches, loc='center left', bbox_to_anchor=(0.95, 0.5), bbox_transform=plt.gcf().transFigure)

        # Include subset_name in the title
        plt.title(f'Marker Relations for {self.subset_name}')

        # Remove axes
        plt.axis('off')

        plt.show()
    
    def calculate_communities(self):
        if not hasattr(self, 'G2_markers'):
            self.marker_projection()
        # Compute the best partition using the Louvain method
        partition = community_louvain.best_partition(self.G2_markers) #result is a dict where key = node and value = community

        # Get the number of unique communities
        num_communities = len(set(partition.values()))

        print(f"Number of communities: {num_communities}")

        # Store the partition for later use
        self.partition = partition
    
    
    # Main method to run most of the graph checks
    def perform_graph_checks(self):
        self.create_bipartite_graph()
        self.sanity_checks()
        self.connectedness()
        self.plot_degree_cdf()
        self.marker_projection()
        self.plot_w_marker_relations()
        self.calculate_communities()
        self.top_five_markers_in_degree()

    
    # CA fitting methods
    def create_contingency_table(self):
        # Create the contingency table
        self.contingency_table = pd.crosstab(self.data_subset['follower_id'], self.data_subset['twitter_name'])
    
    def perform_ca_analysis(self, save_path, n_components=100, n_iter=100):
        try:
            # Initialize a CA object
            ca = prince.CA(
                n_components=n_components,  # Number of components to keep
                n_iter=n_iter,  # Number of iterations for the power method
                copy=True,  # Whether to overwrite the data matrix
                check_input=True,  # Whether to check the input for NaNs and Infs
                engine='sklearn',  # Whether to perform computations in C or Python
                random_state=42  # Random seed for reproducibility
            )

            # Fit the CA model on the contingency table
            ca.fit(self.contingency_table)
            self.ca = ca

            # Get the coordinates of the rows (followers) and columns (brands) 
            row_coordinates = ca.row_coordinates(self.contingency_table)
            column_coordinates = ca.column_coordinates(self.contingency_table)

            # If 'label', 'type', and 'type2' columns exist in the original data, add them to the column coordinates
            if all(item in self.data_subset.columns for item in ['label', 'type', 'type2']):
                column_coordinates = column_coordinates.merge(self.data_subset[['twitter_name', 'label', 'type', 'type2']].drop_duplicates(), left_index=True, right_on='twitter_name')
            else:
                proceed = input("The data has no 'label', 'type', or 'type2' column, do you still want to run and save the CA? (yes/no): ")
                if proceed.lower() != 'yes':
                    return

            # Create a new directory with the name of the edgelist if it doesn't exist
            new_dir_path = os.path.join(save_path, f"{self.edgelist_name}_coords")
            if not os.path.exists(new_dir_path):
                os.makedirs(new_dir_path)

            # Save the row and column coordinates to CSV files in the new directory
            # If a file already exists, add a unique suffix to the filename
            row_file_path = os.path.join(new_dir_path, f'{self.edgelist_name}_row_coordinates.csv')
            column_file_path = os.path.join(new_dir_path, f'{self.edgelist_name}_column_coordinates.csv')
            row_file_path = self.get_unique_filepath(row_file_path)
            column_file_path = self.get_unique_filepath(column_file_path)

            # Save only the first four dimensions and the 'twitter_name', 'label', 'type', and 'type2' columns
            if all(item in column_coordinates.columns for item in ['label', 'type', 'type2']):
                column_coordinates[['twitter_name', 'label', 'type', 'type2'] + list(column_coordinates.columns[:4])].to_csv(column_file_path)
            else:
                column_coordinates.to_csv(column_file_path)

            # Save only the first four dimensions
            row_coordinates.iloc[:, :4].to_csv(row_file_path)

        except Exception as e:
            print(f"Error occurred while performing CA analysis: {str(e)}")
 

    def plot_variance(self):
        # Get the percentage of variance
        percentage_of_variance = self.ca.percentage_of_variance_

        # Create a range of numbers for x axis
        dimensions = range(1, len(percentage_of_variance) + 1)

        # Create the plot
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.bar(dimensions, percentage_of_variance)
        ax.set_xlabel('Dimensions')
        ax.set_ylabel('Inertia (%)')  

        # Remove the upper and rightmost frame
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)

        # Include subset_name in the title
        ax.set_title(f'Inertia Explained per Dimension ({self.subset_name})')

        plt.show()

    def get_unique_filepath(self, filepath):
        import os

        # If the file doesn't exist, return the original filepath
        if not os.path.exists(filepath):
            return filepath

        # If the file exists, ask the user if they want to overwrite it
        overwrite = input(f"{filepath} already exists. Do you want to overwrite it? (yes/no): ")

        if overwrite.lower() == 'yes':
            return filepath

        # If the user doesn't want to overwrite, add a unique suffix to the filename
        base, ext = os.path.splitext(filepath)
        i = 1
        while os.path.exists(filepath):
            filepath = f"{base}_{i}{ext}"
            i += 1

        return filepath
    

    def perform_ca_pipeline(self, save_path):
        print("Creating contingency table...")
        self.create_contingency_table()
        print("Performing CA analysis. Might take some time...")
        self.perform_ca_analysis(save_path, n_components=100, n_iter=100)
        print("Plotting variance...")
        self.plot_variance()


    # Run all
    def run_all(self, save_path):
        print("Starting graph checks...")
        self.perform_graph_checks()
        print("Graph checks complete. Starting CA fitting pipeline...")
        self.perform_ca_pipeline(save_path)
        print("CA pipeline complete.")

