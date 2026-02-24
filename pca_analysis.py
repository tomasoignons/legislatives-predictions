import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns

# Assuming your data is in 'df'
# Step 1: Prepare your data (exclude non-numeric columns if any)
df = pd.read_csv("./data/1999-2024_CHES_dataset_means.csv")
df = df[df["country"] == 6]
df = df[df["electionyear"] == 2024]
features = df.select_dtypes(include=[np.number])

# Remove columns with NaN values
print(f"Original shape: {features.shape}")
features = features.dropna(axis=1)
print(f"After dropping NaN columns: {features.shape}")
print(f"Columns kept: {list(features.columns)}")

# drop specific columns if needed
columns_to_drop = ['year', 'country', 'eastwest', 'eumember', 'party_id', 'vote', 'seat', 'electionyear', 'epvote', 'family', 'chesversion']
features = features.drop(columns=columns_to_drop, errors='ignore')
print(f"After dropping specific columns: {features.shape}")

# ===== STEP 1.5: Remove redundant features =====
print("\n" + "="*70)
print("ANALYZING FEATURE REDUNDANCY")
print("="*70)

# Calculate correlation matrix
correlation_matrix = features.corr().abs()

# Find highly correlated pairs (threshold = 0.85)
correlation_threshold = 0.85
upper_triangle = correlation_matrix.where(
    np.triu(np.ones(correlation_matrix.shape), k=1).astype(bool)
)

# Find features with correlation > threshold
highly_correlated_pairs = []
for column in upper_triangle.columns:
    correlated_features = upper_triangle[column][upper_triangle[column] > correlation_threshold]
    for feature in correlated_features.index:
        highly_correlated_pairs.append((column, feature, upper_triangle[column][feature]))

print(f"\nFound {len(highly_correlated_pairs)} highly correlated pairs (threshold={correlation_threshold}):")
for feat1, feat2, corr in sorted(highly_correlated_pairs, key=lambda x: x[2], reverse=True):
    print(f"  {feat1} <-> {feat2}: {corr:.3f}")

# Strategy to remove redundant features:
# For each correlated pair, keep the feature that captures more variance
# (i.e., has higher standard deviation)
features_to_drop = set()
feature_variance = features.var()

for feat1, feat2, corr in highly_correlated_pairs:
    if feat1 not in features_to_drop and feat2 not in features_to_drop:
        # Drop the one with lower variance
        if feature_variance[feat1] < feature_variance[feat2]:
            features_to_drop.add(feat1)
            print(f"  -> Dropping {feat1} (variance: {feature_variance[feat1]:.3f}) in favor of {feat2} (variance: {feature_variance[feat2]:.3f})")
        else:
            features_to_drop.add(feat2)
            print(f"  -> Dropping {feat2} (variance: {feature_variance[feat2]:.3f}) in favor of {feat1} (variance: {feature_variance[feat1]:.3f})")

# Remove redundant features
features_reduced = features.drop(columns=list(features_to_drop))
print(f"\n{len(features_to_drop)} redundant features removed")
print(f"Remaining features: {features_reduced.shape[1]}")
print(f"\nFINAL FEATURE LIST TO USE:")
print("="*70)
for i, col in enumerate(sorted(features_reduced.columns), 1):
    print(f"  {i:2d}. {col}")
print("="*70)

# Use reduced features for PCA
features = features_reduced

# Visualize correlation matrix before and after
fig, axes = plt.subplots(1, 2, figsize=(20, 8))

# Before reduction
sns.heatmap(features.corr(), cmap='coolwarm', center=0, 
            square=True, ax=axes[0], cbar_kws={'shrink': 0.8})
axes[0].set_title(f'Feature Correlation Matrix (Reduced: {features.shape[1]} features)')
axes[0].tick_params(axis='x', rotation=90, labelsize=8)
axes[0].tick_params(axis='y', rotation=0, labelsize=8)

# Show which features are kept
kept_features_text = f"KEPT FEATURES ({len(features.columns)}):\n" + "\n".join([f"• {col}" for col in sorted(features.columns)])
axes[1].text(0.05, 0.95, kept_features_text, transform=axes[1].transAxes, 
             fontsize=9, verticalalignment='top', family='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
axes[1].axis('off')
axes[1].set_title('Features Selected for Analysis')

plt.tight_layout()
plt.show()

# Step 2: Standardize the data (crucial for PCA!)
scaler = StandardScaler()
scaled_data = scaler.fit_transform(features)

# Step 3: Apply PCA
pca = PCA()
pca_data = pca.fit_transform(scaled_data)

# Step 4: Analyze explained variance
explained_variance = pca.explained_variance_ratio_

# Plot explained variance
plt.figure(figsize=(10, 5))
plt.bar(range(1, len(explained_variance) + 1), explained_variance)
plt.xlabel('Principal Component')
plt.ylabel('Explained Variance Ratio')
plt.title('Explained Variance by Principal Component')
plt.show()

# Cumulative explained variance
cumulative_variance = np.cumsum(explained_variance)
plt.figure(figsize=(10, 5))
plt.plot(range(1, len(cumulative_variance) + 1), cumulative_variance, marker='o')
plt.xlabel('Number of Components')
plt.ylabel('Cumulative Explained Variance')
plt.title('Cumulative Explained Variance')
plt.axhline(y=0.95, color='r', linestyle='--', label='95% variance')
plt.legend()
plt.show()

print(f"Number of components for 95% variance: {np.argmax(cumulative_variance >= 0.95) + 1}")

# ===== DETAILED 95% VARIANCE EXPLANATION =====
print("\n" + "="*70)
print("FEATURES EXPLAINING 95% OF VARIANCE")
print("="*70)

n_components_95 = np.argmax(cumulative_variance >= 0.95) + 1
print(f"\nFirst {n_components_95} components explain 95% of variance")
print(f"Individual contributions:")

for i in range(n_components_95):
    print(f"\n  PC{i+1}: {explained_variance[i]:.2%} of variance (cumulative: {cumulative_variance[i]:.2%})")

print("\n" + "-"*70)
print("TOP FEATURES FOR EACH COMPONENT (up to 95% variance):")
print("-"*70)

# Create loadings dataframe (moved up for this analysis)
loadings_temp = pd.DataFrame(
    pca.components_.T,
    columns=[f'PC{i+1}' for i in range(len(pca.components_))],
    index=features.columns
)

# For each component up to 95%, show top features
for i in range(n_components_95):
    pc_name = f'PC{i+1}'
    print(f"\n{pc_name} ({explained_variance[i]:.2%} of total variance):")
    top_5 = loadings_temp[pc_name].abs().sort_values(ascending=False).head(5)
    for feat, loading in top_5.items():
        sign = "+" if loadings_temp[pc_name][feat] > 0 else "-"
        print(f"  {sign} {feat:30s} {abs(loading):.3f}")

# Now show which features are most important across all these components
print("\n" + "="*70)
print(f"MOST IMPORTANT FEATURES ACROSS FIRST {n_components_95} COMPONENTS")
print("(weighted by variance explained)")
print("="*70)

weighted_importance_95 = (np.abs(loadings_temp.iloc[:, :n_components_95]) * explained_variance[:n_components_95]).sum(axis=1).sort_values(ascending=False)

print(f"\nThese features contribute most to the 95% variance:")
for i, (feat, importance) in enumerate(weighted_importance_95.head(15).items(), 1):
    print(f"  {i:2d}. {feat:30s} {importance:.3f}")

print("="*70)


# Step 5: Get feature importance from principal components
# Create a dataframe of loadings (component weights)
loadings = pd.DataFrame(
    pca.components_.T,
    columns=[f'PC{i+1}' for i in range(len(pca.components_))],
    index=features.columns
)

# Display loadings for first few PCs
print("Feature Loadings for First 3 PCs:")
print(loadings[['PC1', 'PC2', 'PC3']])

# Step 6: Visualize loadings for PC1 and PC2
fig, axes = plt.subplots(1, 2, figsize=(15, 5))

loadings['PC1'].sort_values().plot(kind='barh', ax=axes[0])
axes[0].set_title('Feature Loadings for PC1')
axes[0].set_xlabel('Loading Value')

loadings['PC2'].sort_values().plot(kind='barh', ax=axes[1])
axes[1].set_title('Feature Loadings for PC2')
axes[1].set_xlabel('Loading Value')

plt.tight_layout()
plt.show()

# Step 7: Find most important features overall
# Calculate absolute contribution across top PCs (e.g., first 3)
n_components = 3
importance = np.abs(loadings.iloc[:, :n_components]).sum(axis=1).sort_values(ascending=False)

print("\nMost Important Features (by absolute loading sum):")
print(importance)

# Or use weighted importance by explained variance
weighted_importance = (np.abs(loadings.iloc[:, :n_components]) * explained_variance[:n_components]).sum(axis=1).sort_values(ascending=False)

print("\nMost Important Features (variance-weighted):")
print(weighted_importance)

# ===== STEP 8: Feature selection recommendations =====
print("\n" + "="*70)
print("FEATURE SELECTION RECOMMENDATIONS")
print("="*70)

# For each PC, show top contributing features
n_top_features = 5
print(f"\nTop {n_top_features} features per principal component:")
for i in range(min(5, len(explained_variance))):  # First 5 PCs
    pc_name = f'PC{i+1}'
    print(f"\n{pc_name} (explains {explained_variance[i]:.1%} of variance):")
    top_features = loadings[pc_name].abs().sort_values(ascending=False).head(n_top_features)
    for feat, loading in top_features.items():
        sign = "+" if loadings[pc_name][feat] > 0 else "-"
        print(f"  {sign} {feat}: {abs(loading):.3f}")

# Final recommendation
print("\n" + "="*70)
print("RECOMMENDED FEATURE SET (non-redundant):")
print("="*70)
print(f"\nUse these {len(features.columns)} features for your analysis:")
for i, col in enumerate(sorted(features.columns), 1):
    print(f"  {i:2d}. {col}")

# Save recommended features to a file
recommended_features = sorted(features.columns)
pd.DataFrame({'feature': recommended_features}).to_csv('recommended_features.csv', index=False)
print(f"\n✓ Recommended features saved to 'recommended_features.csv'")

# Also save the top features for 95% variance
n_components_95 = np.argmax(cumulative_variance >= 0.95) + 1
weighted_importance_95_final = (np.abs(loadings.iloc[:, :n_components_95]) * explained_variance[:n_components_95]).sum(axis=1).sort_values(ascending=False)
pd.DataFrame({
    'feature': weighted_importance_95_final.index,
    'importance_score': weighted_importance_95_final.values
}).to_csv('features_for_95_variance.csv', index=False)
print(f"✓ Top features for 95% variance saved to 'features_for_95_variance.csv'")

print("\n" + "="*70)
print(f"Summary: {n_components_95} components explain 95% of variance")
print(f"These {n_components_95} components are built from {len(features.columns)} non-redundant features")
print("="*70)

def biplot(score, coeff, labels=None, pc1=0, pc2=1, party_labels=None):
    plt.figure(figsize=(14, 10))
    
    xs = score[:, pc1]
    ys = score[:, pc2]
    n = coeff.shape[0]
    
    # Plot samples (parties)
    scatter = plt.scatter(xs, ys, alpha=0.6, s=100, c=range(len(xs)), cmap='tab10')
    
    # Add party labels if available
    if party_labels is not None:
        for i, label in enumerate(party_labels):
            plt.annotate(label, (xs[i], ys[i]), fontsize=8, alpha=0.7)
    
    # Plot feature vectors (only top contributing features for clarity)
    scalex = 1.0/(xs.max() - xs.min())
    scaley = 1.0/(ys.max() - ys.min())
    
    # Get top features by absolute contribution to these PCs
    feature_importance = np.abs(coeff[:, pc1]) + np.abs(coeff[:, pc2])
    top_features_idx = np.argsort(feature_importance)[-15:]  # Top 15 features
    
    for i in top_features_idx:
        plt.arrow(0, 0, coeff[i, pc1]*7, coeff[i, pc2]*7, 
                 color='red', alpha=0.6, head_width=0.15, linewidth=1.5)
        if labels is None:
            plt.text(coeff[i, pc1]*7.5, coeff[i, pc2]*7.5, 
                    f"Var{i+1}", color='darkred', ha='center', va='center',
                    fontsize=8, weight='bold')
        else:
            plt.text(coeff[i, pc1]*7.5, coeff[i, pc2]*7.5, 
                    labels[i], color='darkred', ha='center', va='center',
                    fontsize=9, weight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.3))
    
    plt.xlabel(f"PC{pc1+1} ({explained_variance[pc1]:.1%} of variance)", fontsize=12, weight='bold')
    plt.ylabel(f"PC{pc2+1} ({explained_variance[pc2]:.1%} of variance)", fontsize=12, weight='bold')
    plt.title(f'PCA Biplot: Parties and Top Features', fontsize=14, weight='bold')
    plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    plt.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()

# Get party names if available
party_names = df['party'].values if 'party' in df.columns else None
biplot(pca_data, pca.components_, labels=features.columns, party_labels=party_names)